#!/usr/bin/env python3
"""Prospectively locked MovieLens-1M proof of concept for FACET-PREF.

The runner implements a fixed-budget upstream retrieval intervention.  It
builds deterministic preference facets from prefix-only history, learns a
small reference-free adapter exclusively from natural R-block preference
pairs, retrieves exactly 200 BPR candidates plus 200 BPR-novel semantic
candidates, and evaluates the registered G1--G9 promise gate after one sealed
T opening.  The program is append-only and fail-closed; its result and marker
are runner candidates until a source-bound post-exit verifier independently
replays the raw arrays.

No target is used to construct a query, candidate set, scalar score, or rank.
V relevance is used only for the two preregistered locks (BPR identity and the
shared scalar-fusion coefficient).  V preference labels are opened later and
only for the preregistered power audit.  T is opened exactly once after all
test manifests have been durably published.
"""

from __future__ import annotations

import os

# These settings must precede NumPy, Torch, FAISS, Transformers, and tqdm.
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
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TQDM_DISABLE"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import argparse
import hashlib
import importlib.metadata
import io
import json
import math
import platform
import random
import shutil
import sys
import time
import traceback
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn

import caper_poc as core

# caper_poc is the audited numerical dependency and sets both Torch thread
# pools exactly once during import.  Assert rather than calling inter-op setup
# a second time (PyTorch rejects a repeated inter-op call).
if torch.get_num_threads() != 1 or torch.get_num_interop_threads() != 1:
    raise RuntimeError("FACET-PREF requires one Torch intra-op and inter-op thread")

IntegrityError = core.IntegrityError
Interaction = core.Interaction
UserSplit = core.UserSplit
BPRArtifacts = core.BPRArtifacts

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
        "HF_HUB_DISABLE_PROGRESS_BARS",
        "TQDM_DISABLE",
        "TRANSFORMERS_VERBOSITY",
        "HF_HUB_OFFLINE",
        "TRANSFORMERS_OFFLINE",
        "TOKENIZERS_PARALLELISM",
        "PYTHONHASHSEED",
        "PYTHONDONTWRITEBYTECODE",
    )
    if key in os.environ
}

FIXED_EXECUTION_ENVIRONMENT = {
    **{key: "1" for key in (
        "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
    )},
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

METHODS = (
    "selected_bpr",
    "raw_single_centroid_hybrid",
    "raw_multi_facet",
    "single_query_aligned",
    "multi_facet_zero_margin",
    "multi_facet_shuffled_direction",
    "multi_facet_pair_micro",
    "facet_pref",
)
HYBRID_METHODS = METHODS[1:]
CONTROL_METHODS = (
    "raw_multi_facet",
    "single_query_aligned",
    "multi_facet_zero_margin",
    "multi_facet_shuffled_direction",
    "multi_facet_pair_micro",
)
METRICS = (
    "pair_support",
    "spce_at_10",
    "ndcg_at_10",
    "recall_at_10",
    "low_rating_intrusion_at_10",
    "positive_union_recall",
)
RETRIEVAL_DIAGNOSTICS = (
    "pre_exclusion_cross_facet_overlap",
    "eligible_cross_facet_overlap",
    "higher_facet_duplicates_removed",
    "lower_owner_violation_count",
    "eligible_facet0_count",
    "eligible_facet1_count",
)

LOCKED_CONFIG_SHA256 = "28a933dd671c2d7d994b25b56acb554c72ae4500c352b670e67d7e857fa62d5d"
LOCKED_PROTOCOL_SHA256 = "03af0f865c97d7489eac1c11805705224bdf00f2f0f2d97d6a6bae030677527e"


@dataclass(frozen=True)
class FacetDescriptor:
    """All prefix-only state required to construct raw or aligned queries."""

    user_id: int
    raw_facets: np.ndarray
    facet_members: tuple[tuple[int, ...], ...]
    liked_centroid: np.ndarray
    dislike_centroid: np.ndarray
    facet_support: np.ndarray
    normalized_prefix_length: float
    history_items: frozenset[int]


@dataclass(frozen=True)
class RetrievalRecord:
    collaborative: tuple[int, ...]
    semantic: tuple[int, ...]
    union: tuple[int, ...]
    ranking: tuple[int, ...]
    scores: np.ndarray
    raw_bpr_scores: np.ndarray
    raw_semantic_scores: np.ndarray
    facet_queries: np.ndarray
    facet_winners: np.ndarray
    quota_utilization: tuple[int, ...]
    retrieval_diagnostics: tuple[int, ...]
    semantic_owners: tuple[int, ...]


@dataclass(frozen=True)
class PairCorpus:
    user_ids: np.ndarray
    chosen_items: np.ndarray
    rejected_items: np.ndarray
    facet_inputs: np.ndarray
    facet_mask: np.ndarray
    chosen_vectors: np.ndarray
    rejected_vectors: np.ndarray
    assigned_facets: np.ndarray
    macro_weights: np.ndarray
    pair_keys: tuple[tuple[int, int, int], ...]
    diagnostics: Mapping[str, Any]


class RunnerLock:
    """Exclusive lock with PID liveness and owner-token verification."""

    def __init__(self, path: Path, protocol_sha256: str) -> None:
        self.path = path
        self.protocol_sha256 = protocol_sha256
        self.token = uuid.uuid4().hex
        self.acquired = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "facet-pref-runner-lock-v1",
            "pid": os.getpid(),
            "token": self.token,
            "protocol_sha256": self.protocol_sha256,
            "created_utc": core.utc_now(),
        }
        try:
            core.publish_json_no_overwrite(self.path, payload)
        except FileExistsError as exc:
            try:
                current = json.loads(self.path.read_text(encoding="utf-8"))
                owner = int(current.get("pid", -1))
            except Exception as parse_exc:
                raise IntegrityError("Unreadable FACET-PREF runner lock") from parse_exc
            state = "live" if core.process_is_alive(owner) else "stale"
            raise IntegrityError(f"FACET-PREF runner lock exists ({state} PID {owner})") from exc
        self.acquired = True

    def release(self) -> None:
        if not self.acquired:
            return
        current = json.loads(self.path.read_text(encoding="utf-8"))
        if current.get("token") != self.token or int(current.get("pid", -1)) != os.getpid():
            raise IntegrityError("FACET-PREF runner-lock ownership changed")
        self.path.unlink()
        core.fsync_directory(self.path.parent)
        self.acquired = False


class QueryAdapter(nn.Module):
    """Shared bounded adapter; its output layer is exactly zero-initialized."""

    def __init__(self, input_dimension: int, embedding_dimension: int, hidden: int) -> None:
        super().__init__()
        self.hidden = nn.Linear(input_dimension, hidden)
        self.output = nn.Linear(hidden, embedding_dimension)
        nn.init.zeros_(self.output.weight)
        nn.init.zeros_(self.output.bias)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.output(torch.tanh(self.hidden(inputs)))


def _normalise(vector: np.ndarray) -> np.ndarray:
    value = np.asarray(vector, dtype=np.float32)
    norm = float(np.linalg.norm(value))
    if not math.isfinite(norm) or norm <= 1e-12:
        raise IntegrityError("Cannot normalize a zero or nonfinite query")
    return np.ascontiguousarray(value / norm, dtype=np.float32)


def _normalise_rows_torch(matrix: torch.Tensor) -> torch.Tensor:
    return matrix / torch.clamp(torch.linalg.vector_norm(matrix, dim=-1, keepdim=True), min=1e-12)


def _npz_bytes(**arrays: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    np.savez_compressed(buffer, **arrays)
    return buffer.getvalue()


def _safe_quantile_normalize(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float32)
    lower, upper = np.percentile(array.astype(np.float64), [5.0, 95.0])
    span = max(float(upper - lower), 1e-6)
    result = np.asarray(
        np.clip((array - np.float32(lower)) / np.float32(span), 0.0, 1.0),
        dtype=np.float32,
    )
    if not np.all(np.isfinite(result)):
        raise IntegrityError("Quantile normalization produced nonfinite values")
    return result


def rank_descending(items: Sequence[int], scores: np.ndarray, movie_ids: Sequence[int]) -> tuple[int, ...]:
    if len(items) != len(scores):
        raise IntegrityError("Ranking items and scores differ in length")
    order = sorted(
        range(len(items)),
        key=lambda row: (-float(scores[row]), int(movie_ids[int(items[row])])),
    )
    return tuple(int(items[row]) for row in order)


def validate_config(config: Mapping[str, Any]) -> None:
    for section in (
        "dataset",
        "embedding",
        "bpr",
        "facets",
        "adapter",
        "retrieval",
        "alignment",
        "ranking",
        "controls",
        "validation",
        "power_audit",
        "evaluation",
        "promise_gate",
        "execution",
    ):
        if not isinstance(config.get(section), Mapping):
            raise ValueError(f"Missing configuration section: {section}")
    dataset = config["dataset"]
    retrieval = config["retrieval"]
    alignment = config["alignment"]
    evaluation = config["evaluation"]
    gate = config["promise_gate"]
    seeds = [int(value) for value in config.get("optimization_seeds", [])]
    if seeds != [20260827, 20260828, 20260829]:
        raise ValueError("FACET-PREF requires optimization seeds 20260827..20260829")
    if {key: float(value) for key, value in dataset["split_fractions"].items()} != {
        "A": 0.6, "R": 0.2, "V": 0.1, "T": 0.1
    }:
        raise ValueError("FACET-PREF requires A/R/V/T=60/20/10/10")
    if dataset.get("split_unit") != "per_user_indivisible_timestamp_groups":
        raise ValueError("Timestamp groups must remain indivisible")
    if str(dataset.get("expected_archive_sha256")) != (
        "a6898adb50b9ca05aa231689da44c217cb524e7ebd39d264c56e2832f2c54e20"
    ):
        raise ValueError("FACET-PREF requires the locked official ML-1M archive")
    if dataset["historical_slices"] != {"caper": [0, 1000], "ravel": [1000, 2000]} or dataset["facet_pref_slice"] != [2000, 4000]:
        raise ValueError("Locked CAPER/RAVEL/FACET slices changed")
    if int(dataset["minimum_eligible_users_before_slice"]) < 4000:
        raise ValueError("At least 4,000 eligible users are required")
    if int(config["determinism_seed"]) != 20260817:
        raise ValueError("Cohort hash seed changed")
    if not bool(dataset.get("exclude_demographics", False)):
        raise ValueError("Demographics must be excluded")
    if retrieval.get("index_kind") != "IndexFlatIP" or retrieval.get("metric") != "inner_product":
        raise ValueError("Exact inner-product FAISS indexes are required")
    for key, expected in (
        ("collaborative_candidates_exact", 200),
        ("semantic_candidates_exact", 200),
        ("union_candidates_exact", 400),
        ("semantic_search_depth_per_query", 700),
    ):
        if int(retrieval[key]) != expected:
            raise ValueError(f"retrieval.{key} must equal {expected}")
    if int(config["facets"].get("maximum_facets", 0)) != 2 or int(config["facets"].get("maximum_iterations", 0)) != 8:
        raise ValueError("Facet clustering must stop after at most eight iterations")
    if int(config["embedding"]["dimension"]) != 384 or int(config["adapter"]["input_dimension"]) != 1154:
        raise ValueError("Locked SentenceTransformer/adapter dimensions changed")
    if not math.isclose(float(config["facets"]["dislike_centroid_weight"]), 0.25):
        raise ValueError("The global dislike weight must equal 0.25")
    if not math.isclose(float(config["adapter"]["query_displacement_bound"]), 0.25):
        raise ValueError("The bounded adapter scale must equal 0.25")
    if float(alignment["margin"]) <= 0.0:
        raise ValueError("The registered FACET-PREF margin must be positive")
    if float(alignment["beta"]) <= 0.0:
        raise ValueError("SimPO beta must be positive")
    if int(alignment["maximum_training_pairs"]) < 5000:
        raise ValueError("The alignment cap cannot be below the R support floor")
    if int(alignment["minimum_uncapped_natural_pairs"]) < 5000:
        raise ValueError("R requires at least 5,000 natural pairs")
    if int(alignment["minimum_uncapped_pair_bearing_users"]) < 1000:
        raise ValueError("R requires at least 1,000 pair-bearing users")
    if int(evaluation["minimum_fixed_test_pairs"]) < 2000:
        raise ValueError("T requires at least 2,000 fixed natural pairs")
    if int(evaluation["minimum_test_pair_bearing_users"]) < 500:
        raise ValueError("T requires at least 500 pair-bearing users")
    if int(evaluation["bootstrap_draws"]) != 10000:
        raise ValueError("The final bootstrap requires exactly 10,000 draws")
    if int(evaluation["bootstrap_seed"]) != 20263117:
        raise ValueError("The final bootstrap seed changed")
    if int(evaluation["maximum_test_pairs_per_user"]) != 100:
        raise ValueError("The fixed pair cap must equal 100")
    if not str(evaluation["test_pair_hash_format"]).startswith("20263118:"):
        raise ValueError("The fixed pair hash seed changed")
    power = config["power_audit"]
    fixed_power = (
        float(power["alternative_delta"]), int(power["simulated_experiments"]),
        int(power["sample_users_with_replacement"]), int(power["inner_bootstrap_draws"]),
        int(power["comparison_seeds"]["raw_single_centroid_hybrid"]),
        int(power["comparison_seeds"]["selected_bpr"]),
    )
    if fixed_power != (0.005, 2000, 500, 1000, 20263119, 20263120):
        raise ValueError("The preregistered power audit changed")
    checks = (
        (gate["G2"]["minimum_pair_support_point_gain"], 0.02),
        (gate["G2"]["minimum_positive_union_recall_point_gain"], 0.02),
        (gate["G3"]["minimum_spce_at_10_point_gain_each"], 0.005),
        (gate["G4"]["minimum_ndcg_at_10_point_delta"], -0.0002),
        (gate["G4"]["minimum_ndcg_at_10_lower_bound_strict"], -0.001),
        (gate["G4"]["minimum_recall_at_10_lower_bound_strict"], -0.002),
        (gate["G4"]["maximum_intrusion_at_10_increase_upper_bound"], 0.002),
        (gate["G6"]["minimum_common_pair_endpoint_cosupport"], 0.10),
        (gate["G6"]["minimum_changed_spce_pair_outcome_fraction"], 0.02),
        (gate["G8"]["maximum_worst_seed_p95_latency_ms"], 5.0),
        (gate["G8"]["maximum_worst_seed_p95_latency_ratio"], 1.25),
    )
    if any(not math.isclose(float(actual), expected, rel_tol=0.0, abs_tol=1e-12) for actual, expected in checks):
        raise ValueError("One or more locked G1-G9 thresholds changed")


def splitter_dataset_config(config: Mapping[str, Any]) -> Mapping[str, Any]:
    """Translate the locked Cycle-4 schema to the established audited splitter."""
    dataset = config["dataset"]
    return {
        "positive_rating_min": int(dataset["positive_rating_min"]),
        "minimum_train_events": int(dataset["minimum_A_events"]),
        "minimum_positive_history": int(dataset["minimum_distinct_positive_A_items"]),
        "minimum_total_events": int(dataset["minimum_total_events"]),
        "maximum_users": None,
        "minimum_test_users": int(dataset["minimum_eligible_users_before_slice"]),
        "stable_subset_seed": int(config["determinism_seed"]),
    }


def acquire_locked_archive(
    destination: Path,
    official_url: str,
    expected_sha256: str,
    local_source: Path | None,
) -> tuple[str, str]:
    expected = expected_sha256.lower()
    if local_source is None:
        return core.acquire_official_zip(destination, official_url, expected), "official_download"
    source = local_source.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if core.sha256_file(source) != expected:
        raise IntegrityError("Local MovieLens archive does not match the locked SHA-256")
    temporary = destination.with_name(f".{destination.name}.copy.{os.getpid()}.{uuid.uuid4().hex}")
    try:
        with source.open("rb") as incoming, temporary.open("xb") as outgoing:
            shutil.copyfileobj(incoming, outgoing, length=1024 * 1024)
            outgoing.flush()
            os.fsync(outgoing.fileno())
        if core.sha256_file(temporary) != expected:
            raise IntegrityError("Archive changed while being copied")
        os.link(temporary, destination)
        core.fsync_directory(destination.parent)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return expected, "authenticated_local_copy"


def derive_facet_cohort(
    interactions: Sequence[Interaction], config: Mapping[str, Any]
) -> tuple[list[UserSplit], Mapping[str, Any]]:
    dataset = config["dataset"]
    eligible, diagnostics = core.chronological_timestamp_group_splits(
        interactions, splitter_dataset_config(config)
    )
    minimum_distinct = int(config["dataset"]["minimum_distinct_positive_A_items"])
    positive_min = int(config["dataset"]["positive_rating_min"])
    before_distinct_filter = len(eligible)
    eligible = [
        split
        for split in eligible
        if len({event.item_index for event in split.train if event.rating >= positive_min})
        >= minimum_distinct
    ]
    diagnostics = {
        **dict(diagnostics),
        "eligible_before_distinct_positive_A_filter": before_distinct_filter,
        "excluded_non_distinct_positive_A": before_distinct_filter - len(eligible),
        "distinct_positive_A_requirement": minimum_distinct,
    }
    seed = int(config["determinism_seed"])
    ordered = sorted(
        eligible,
        key=lambda split: (
            hashlib.sha256(f"{seed}:{split.user_id}".encode("ascii")).hexdigest(),
            split.user_id,
        ),
    )
    if len(ordered) < 4000:
        raise IntegrityError(f"Only {len(ordered)} eligible users; at least 4,000 required")
    caper = ordered[0:1000]
    ravel = ordered[1000:2000]
    facet = ordered[2000:4000]
    sets = [{split.user_id for split in cohort} for cohort in (caper, ravel, facet)]
    if tuple(map(len, (caper, ravel, facet))) != (1000, 1000, 2000):
        raise IntegrityError("Prospective cohort sizes changed")
    if sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2]:
        raise IntegrityError("CAPER/RAVEL/FACET cohorts are not pairwise disjoint")
    return sorted(facet, key=lambda split: split.user_id), {
        **dict(diagnostics),
        "eligible_before_hash_slice": len(ordered),
        "ordering_key": f"SHA256({seed}:user_id), then numeric user_id",
        "caper_slice": [0, 1000],
        "ravel_slice": [1000, 2000],
        "facet_slice": [2000, 4000],
        "caper_user_ids_sha256": core.sha256_bytes(core.canonical_json_bytes(sorted(sets[0]))),
        "ravel_user_ids_sha256": core.sha256_bytes(core.canonical_json_bytes(sorted(sets[1]))),
        "facet_user_ids_sha256": core.sha256_bytes(core.canonical_json_bytes(sorted(sets[2]))),
        "caper_user_ids": sorted(sets[0]),
        "ravel_user_ids": sorted(sets[1]),
        "facet_user_ids": sorted(sets[2]),
        "pairwise_intersection_counts": [
            len(sets[0] & sets[1]), len(sets[0] & sets[2]), len(sets[1] & sets[2])
        ],
        "cohorts_pairwise_disjoint": True,
    }


def sealed_stage_views(
    splits: Sequence[UserSplit],
) -> tuple[list[UserSplit], list[UserSplit], list[UserSplit]]:
    a_only = [UserSplit(split.user_id, split.train, (), (), ()) for split in splits]
    ar_only = [UserSplit(split.user_id, split.train, split.alignment, (), ()) for split in splits]
    arv_only = [
        UserSplit(split.user_id, split.train, split.alignment, split.validation, ())
        for split in splits
    ]
    return a_only, ar_only, arv_only


def _distinct_positive_items(
    history: Sequence[Interaction], positive_min: int
) -> tuple[int, ...]:
    return tuple(sorted({event.item_index for event in history if event.rating >= positive_min}))


def _dislike_centroid(
    history: Sequence[Interaction], vectors: np.ndarray, dislike_max: int
) -> np.ndarray:
    disliked = sorted({event.item_index for event in history if event.rating <= dislike_max})
    if not disliked:
        return np.zeros(vectors.shape[1], dtype=np.float32)
    return _normalise(np.mean(vectors[np.asarray(disliked, dtype=np.int64)], axis=0))


def _spherical_two_means(
    positive_items: Sequence[int],
    semantic_vectors: np.ndarray,
    movie_ids: Sequence[int],
    maximum_iterations: int,
) -> tuple[tuple[int, ...], ...]:
    """Deterministic F<=2 spherical clustering from the locked protocol."""
    items = tuple(sorted(set(map(int, positive_items)), key=lambda item: int(movie_ids[item])))
    if not items:
        raise IntegrityError("Facet construction has no positive prefix item")
    if len(items) == 1:
        return (items,)
    first_seed, second_seed = _least_similar_seed_pair(
        items, semantic_vectors, movie_ids
    )
    centroids = np.stack((semantic_vectors[first_seed], semantic_vectors[second_seed])).astype(np.float32)
    previous: tuple[int, ...] | None = None
    for _iteration in range(maximum_iterations):
        similarities = semantic_vectors[np.asarray(items, dtype=np.int64)] @ centroids.T
        # np.argmax selects canonical facet 0 on an assignment tie.
        assignments = tuple(map(int, np.argmax(similarities, axis=1)))
        clusters = [
            tuple(item for item, assignment in zip(items, assignments, strict=True) if assignment == facet)
            for facet in range(2)
        ]
        if not clusters[0] or not clusters[1]:
            return (items,)
        # Facet labels are canonical after every assignment/update iteration,
        # not merely at convergence.  Relabel assignments before the stability
        # comparison so an index swap cannot masquerade as oscillation.
        canonical_order = sorted(
            range(2),
            key=lambda facet: min(int(movie_ids[item]) for item in clusters[facet]),
        )
        if canonical_order != [0, 1]:
            inverse = {old: new for new, old in enumerate(canonical_order)}
            assignments = tuple(inverse[assignment] for assignment in assignments)
            clusters = [clusters[old] for old in canonical_order]
        if assignments == previous:
            break
        previous = assignments
        centroids = np.stack(
            [_normalise(np.mean(semantic_vectors[np.asarray(cluster, dtype=np.int64)], axis=0)) for cluster in clusters]
        ).astype(np.float32)
    if previous is None:
        raise IntegrityError("Facet clustering did not execute")
    clusters = [
        tuple(item for item, assignment in zip(items, previous, strict=True) if assignment == facet)
        for facet in range(2)
    ]
    if not clusters[0] or not clusters[1]:
        return (items,)
    clusters.sort(key=lambda cluster: min(int(movie_ids[item]) for item in cluster))
    return tuple(clusters)


def _least_similar_seed_pair(
    movie_indices: Sequence[int],
    semantic_vectors: np.ndarray,
    movie_ids: Sequence[int],
) -> tuple[int, int]:
    """Vectorized exact least-cosine pair with lexicographic ID tie break."""
    items = tuple(
        sorted(set(map(int, movie_indices)), key=lambda item: int(movie_ids[item]))
    )
    if len(items) < 2:
        raise IntegrityError("Least-similar initialization requires two items")
    matrix = np.ascontiguousarray(
        semantic_vectors[np.asarray(items, dtype=np.int64)], dtype=np.float32
    )
    cosine = matrix @ matrix.T
    left, right = np.triu_indices(len(items), k=1)
    values = cosine[left, right]
    # `items` is numeric-movie-ID sorted and np.triu_indices is row-major, so
    # np.argmin's first exact tie is the lexicographically smallest ID pair.
    winner = int(np.argmin(values))
    return items[int(left[winner])], items[int(right[winner])]


def build_facet_descriptor(
    user_id: int,
    history: Sequence[Interaction],
    semantic_vectors: np.ndarray,
    movie_ids: Sequence[int],
    config: Mapping[str, Any],
    force_single: bool = False,
) -> FacetDescriptor:
    positive_min = int(config["dataset"]["positive_rating_min"])
    dislike_max = int(config["dataset"]["dislike_rating_max"])
    positive_items = _distinct_positive_items(history, positive_min)
    if not positive_items:
        raise IntegrityError("Eligible prefix unexpectedly has no positive item")
    if force_single:
        clusters: tuple[tuple[int, ...], ...] = (positive_items,)
    else:
        clusters = _spherical_two_means(
            positive_items,
            semantic_vectors,
            movie_ids,
            int(config["facets"]["maximum_iterations"]),
        )
    dislike = _dislike_centroid(history, semantic_vectors, dislike_max)
    weight = float(config["facets"]["dislike_centroid_weight"])
    raw_queries = np.stack(
        [
            _normalise(
                np.mean(semantic_vectors[np.asarray(cluster, dtype=np.int64)], axis=0)
                - weight * dislike
            )
            for cluster in clusters
        ]
    ).astype(np.float32)
    liked = _normalise(
        np.mean(semantic_vectors[np.asarray(positive_items, dtype=np.int64)], axis=0)
    )
    support = np.asarray([len(cluster) / len(positive_items) for cluster in clusters], dtype=np.float32)
    return FacetDescriptor(
        user_id=int(user_id),
        raw_facets=np.ascontiguousarray(raw_queries, dtype=np.float32),
        facet_members=tuple(tuple(map(int, cluster)) for cluster in clusters),
        liked_centroid=liked,
        dislike_centroid=dislike,
        facet_support=support,
        normalized_prefix_length=float(
            min(len(history), int(config["adapter"]["prefix_length_cap_events"]))
            / int(config["adapter"]["prefix_length_cap_events"])
        ),
        history_items=frozenset(event.item_index for event in history),
    )


def descriptor_inputs(descriptor: FacetDescriptor) -> np.ndarray:
    count, dimension = descriptor.raw_facets.shape
    values = np.concatenate(
        (
            descriptor.raw_facets,
            np.repeat(descriptor.liked_centroid.reshape(1, dimension), count, axis=0),
            np.repeat(descriptor.dislike_centroid.reshape(1, dimension), count, axis=0),
            descriptor.facet_support.reshape(count, 1),
            np.full((count, 1), descriptor.normalized_prefix_length, dtype=np.float32),
        ),
        axis=1,
    )
    return np.ascontiguousarray(values, dtype=np.float32)


def apply_adapter(
    descriptor: FacetDescriptor,
    adapter: QueryAdapter | None,
    adapter_scale: float,
) -> np.ndarray:
    if adapter is None:
        return descriptor.raw_facets.copy()
    adapter.eval()
    with torch.no_grad():
        raw = torch.from_numpy(descriptor.raw_facets)
        residual = adapter(torch.from_numpy(descriptor_inputs(descriptor)))
        residual = residual / torch.clamp(
            torch.linalg.vector_norm(residual, dim=1, keepdim=True), min=1.0
        )
        queries = _normalise_rows_torch(raw + float(adapter_scale) * residual)
    result = np.ascontiguousarray(queries.cpu().numpy(), dtype=np.float32)
    if not np.all(np.isfinite(result)):
        raise IntegrityError("Aligned query contains nonfinite values")
    return result


def build_descriptor_manifest(
    splits: Sequence[UserSplit],
    semantic_vectors: np.ndarray,
    movie_ids: Sequence[int],
    config: Mapping[str, Any],
    stage: str,
) -> tuple[dict[int, FacetDescriptor], dict[int, FacetDescriptor], list[Mapping[str, Any]]]:
    if stage not in {"R", "V", "T"}:
        raise ValueError(stage)
    full: dict[int, FacetDescriptor] = {}
    single: dict[int, FacetDescriptor] = {}
    rows: list[Mapping[str, Any]] = []
    for split in splits:
        history = (
            split.train
            if stage == "R"
            else (*split.train, *split.alignment)
            if stage == "V"
            else (*split.train, *split.alignment, *split.validation)
        )
        descriptor = build_facet_descriptor(
            split.user_id, history, semantic_vectors, movie_ids, config, False
        )
        single_descriptor = build_facet_descriptor(
            split.user_id, history, semantic_vectors, movie_ids, config, True
        )
        full[split.user_id] = descriptor
        single[split.user_id] = single_descriptor
        rows.append(
            {
                "stage": stage,
                "user_id": split.user_id,
                "history_event_count": len(history),
                "history_max_timestamp": max(event.timestamp for event in history),
                "active_facets": int(descriptor.raw_facets.shape[0]),
                "facet_member_movie_ids": [
                    [int(movie_ids[item]) for item in cluster] for cluster in descriptor.facet_members
                ],
                "raw_facet_query_sha256": core.sha256_bytes(descriptor.raw_facets.tobytes(order="C")),
                "single_query_sha256": core.sha256_bytes(single_descriptor.raw_facets.tobytes(order="C")),
                "descriptor_input_sha256": core.sha256_bytes(descriptor_inputs(descriptor).tobytes(order="C")),
                "current_block_identity_or_outcome_joined": False,
                "uses_demographics": False,
            }
        )
    return full, single, rows


def natural_pairs(
    events: Sequence[Interaction],
    minimum_gap: int,
    maximum: int,
    hash_seed: int,
    user_id: int,
    movie_ids: Sequence[int],
) -> tuple[list[tuple[int, int]], int]:
    ordered = sorted(events, key=lambda event: (int(movie_ids[event.item_index]), event.ordinal))
    if len({event.item_index for event in ordered}) != len(ordered):
        raise IntegrityError("Fixed preference block contains repeated movie IDs")
    pairs: list[tuple[int, int]] = []
    for left in range(len(ordered)):
        for right in range(left + 1, len(ordered)):
            gap = ordered[left].rating - ordered[right].rating
            if abs(gap) < minimum_gap:
                continue
            pairs.append(
                (ordered[left].item_index, ordered[right].item_index)
                if gap > 0
                else (ordered[right].item_index, ordered[left].item_index)
            )
    raw_count = len(pairs)
    if len(pairs) > maximum:
        pairs = sorted(
            pairs,
            key=lambda pair: (
                hashlib.sha256(
                    (
                        f"{hash_seed}:{user_id}:"
                        f"{min(int(movie_ids[pair[0]]), int(movie_ids[pair[1]]))}:"
                        f"{max(int(movie_ids[pair[0]]), int(movie_ids[pair[1]]))}"
                    ).encode("ascii")
                ).hexdigest(),
                min(int(movie_ids[pair[0]]), int(movie_ids[pair[1]])),
                max(int(movie_ids[pair[0]]), int(movie_ids[pair[1]])),
            ),
        )[:maximum]
    return pairs, raw_count


def _pair_training_key(
    user_id: int, chosen: int, rejected: int, movie_ids: Sequence[int], seed: int
) -> tuple[str, int, int, int]:
    low = min(int(movie_ids[chosen]), int(movie_ids[rejected]))
    high = max(int(movie_ids[chosen]), int(movie_ids[rejected]))
    return (
        hashlib.sha256(f"{seed}:{user_id}:{low}:{high}".encode("ascii")).hexdigest(),
        user_id,
        low,
        high,
    )


def build_pair_corpus(
    splits: Sequence[UserSplit],
    descriptors: Mapping[int, FacetDescriptor],
    semantic_vectors: np.ndarray,
    movie_ids: Sequence[int],
    config: Mapping[str, Any],
) -> tuple[PairCorpus, list[Mapping[str, Any]]]:
    """Join R after descriptor publication and apply one method-independent cap."""
    gap = int(config["dataset"]["preference_pair_minimum_rating_gap"])
    cap_seed = int(str(config["alignment"]["pair_cap_hash_format"]).split(":", 1)[0])
    uncapped_rows: list[tuple[int, int, int, int]] = []
    for split in splits:
        events = sorted(split.alignment, key=lambda event: (event.timestamp, event.ordinal))
        if len({event.item_index for event in events}) != len(events):
            raise IntegrityError("R contains repeated movie IDs for one user")
        for left in range(len(events)):
            for right in range(left + 1, len(events)):
                rating_gap = events[left].rating - events[right].rating
                if abs(rating_gap) < gap:
                    continue
                chosen, rejected = (
                    (events[left].item_index, events[right].item_index)
                    if rating_gap > 0
                    else (events[right].item_index, events[left].item_index)
                )
                descriptor = descriptors[split.user_id]
                assigned = int(np.argmax(descriptor.raw_facets @ semantic_vectors[chosen]))
                uncapped_rows.append((split.user_id, chosen, rejected, assigned))
    raw_pair_count = len(uncapped_rows)
    raw_users = len({row[0] for row in uncapped_rows})
    uncapped_counts: dict[int, int] = defaultdict(int)
    for row in uncapped_rows:
        uncapped_counts[row[0]] += 1
    if raw_pair_count < int(config["alignment"]["minimum_uncapped_natural_pairs"]):
        raise IntegrityError("R has fewer than 5,000 natural preference pairs")
    if raw_users < int(config["alignment"]["minimum_uncapped_pair_bearing_users"]):
        raise IntegrityError("R has fewer than 1,000 pair-bearing users")
    by_user: dict[int, list[tuple[int, int, int, int]]] = defaultdict(list)
    for row in uncapped_rows:
        by_user[row[0]].append(row)
    ranked_rows: list[tuple[int, str, tuple[int, int, int, int]]] = []
    per_user_cap = int(config["alignment"]["maximum_pairs_per_user"])
    for user_id in sorted(by_user):
        ordered = sorted(
            by_user[user_id],
            key=lambda row: _pair_training_key(row[0], row[1], row[2], movie_ids, cap_seed),
        )[:per_user_cap]
        for within_rank, row in enumerate(ordered):
            pair_hash = _pair_training_key(row[0], row[1], row[2], movie_ids, cap_seed)[0]
            ranked_rows.append((within_rank, pair_hash, row))
    rows = [
        value[2]
        for value in sorted(ranked_rows, key=lambda value: (value[0], value[1]))[
            : int(config["alignment"]["maximum_training_pairs"])
        ]
    ]
    selected_users = {row[0] for row in rows}
    if not rows:
        raise IntegrityError("The prospective R cap is empty")
    maximum_facets = int(config["facets"]["maximum_facets"])
    input_dim = semantic_vectors.shape[1] * 3 + 2
    facet_inputs = np.zeros((len(rows), maximum_facets, input_dim), dtype=np.float32)
    facet_mask = np.zeros((len(rows), maximum_facets), dtype=np.bool_)
    for index, (user_id, _chosen, _rejected, _assigned) in enumerate(rows):
        inputs = descriptor_inputs(descriptors[user_id])
        facet_inputs[index, : len(inputs)] = inputs
        facet_mask[index, : len(inputs)] = True
    # User x assigned-facet macro weights.
    by_user_facet: dict[tuple[int, int], int] = defaultdict(int)
    facets_by_user: dict[int, set[int]] = defaultdict(set)
    for user_id, _chosen, _rejected, assigned in rows:
        by_user_facet[(user_id, assigned)] += 1
        facets_by_user[user_id].add(assigned)
    user_count = len(facets_by_user)
    weights = np.asarray(
        [
            1.0
            / user_count
            / len(facets_by_user[user_id])
            / by_user_facet[(user_id, assigned)]
            for user_id, _chosen, _rejected, assigned in rows
        ],
        dtype=np.float64,
    )
    weights = np.asarray(weights / np.mean(weights), dtype=np.float32)
    keys = tuple((row[0], row[1], row[2]) for row in rows)
    if len(keys) != len(set(keys)):
        raise IntegrityError("The fixed R corpus contains duplicate pair identities")
    serializable = [
        {
            "user_id": user_id,
            "chosen_movie_id": int(movie_ids[chosen]),
            "rejected_movie_id": int(movie_ids[rejected]),
            "assigned_raw_facet": assigned,
            "pair_cap_hash": _pair_training_key(user_id, chosen, rejected, movie_ids, cap_seed)[0],
            "pair_direction_joined_after_descriptor_publication": True,
        }
        for user_id, chosen, rejected, assigned in rows
    ]
    corpus = PairCorpus(
        user_ids=np.asarray([row[0] for row in rows], dtype=np.int64),
        chosen_items=np.asarray([row[1] for row in rows], dtype=np.int64),
        rejected_items=np.asarray([row[2] for row in rows], dtype=np.int64),
        facet_inputs=facet_inputs,
        facet_mask=facet_mask,
        chosen_vectors=np.ascontiguousarray(semantic_vectors[np.asarray([row[1] for row in rows])], dtype=np.float32),
        rejected_vectors=np.ascontiguousarray(semantic_vectors[np.asarray([row[2] for row in rows])], dtype=np.float32),
        assigned_facets=np.asarray([row[3] for row in rows], dtype=np.int64),
        macro_weights=weights,
        pair_keys=keys,
        diagnostics={
            "raw_natural_pairs": raw_pair_count,
            "raw_pair_bearing_users": raw_users,
            "uncapped_pair_counts_by_user": {
                str(user_id): uncapped_counts.get(user_id, 0)
                for user_id in sorted(descriptors)
            },
            "selected_pairs": len(rows),
            "selected_pair_bearing_users": len(selected_users),
            "per_user_cap": per_user_cap,
            "global_cap": int(config["alignment"]["maximum_training_pairs"]),
            "cap_order": "within-user pair-hash rank, then pair hash",
            "method_independent_pair_ids_and_directions": True,
            "targets_injected": False,
        },
    )
    return corpus, serializable


def single_query_corpus(
    base: PairCorpus,
    single_descriptors: Mapping[int, FacetDescriptor],
) -> PairCorpus:
    inputs = np.zeros_like(base.facet_inputs)
    mask = np.zeros_like(base.facet_mask)
    for row, user_id in enumerate(base.user_ids):
        value = descriptor_inputs(single_descriptors[int(user_id)])
        if len(value) != 1:
            raise IntegrityError("Single-query corpus unexpectedly has multiple facets")
        inputs[row, 0] = value[0]
        mask[row, 0] = True
    counts: dict[int, int] = defaultdict(int)
    for user_id in base.user_ids:
        counts[int(user_id)] += 1
    weights = np.asarray(
        [1.0 / len(counts) / counts[int(user_id)] for user_id in base.user_ids],
        dtype=np.float64,
    )
    weights = np.asarray(weights / np.mean(weights), dtype=np.float32)
    return PairCorpus(
        user_ids=base.user_ids,
        chosen_items=base.chosen_items,
        rejected_items=base.rejected_items,
        facet_inputs=inputs,
        facet_mask=mask,
        chosen_vectors=base.chosen_vectors,
        rejected_vectors=base.rejected_vectors,
        assigned_facets=np.zeros_like(base.assigned_facets),
        macro_weights=weights,
        pair_keys=base.pair_keys,
        diagnostics={**dict(base.diagnostics), "query_family": "single_centroid"},
    )


def _adapter_queries_torch(
    model: QueryAdapter,
    inputs: torch.Tensor,
    mask: torch.Tensor,
    embedding_dimension: int,
    scale: float,
) -> torch.Tensor:
    raw = inputs[..., :embedding_dimension]
    residual = model(inputs)
    residual = residual / torch.clamp(torch.linalg.vector_norm(residual, dim=-1, keepdim=True), min=1.0)
    queries = _normalise_rows_torch(raw + float(scale) * residual)
    return torch.where(mask.unsqueeze(-1), queries, torch.zeros_like(queries))


def train_adapter(
    corpus: PairCorpus,
    config: Mapping[str, Any],
    seed: int,
    margin: float,
    weighting: str,
    shuffled_direction: bool,
    initial_state: Mapping[str, torch.Tensor] | None = None,
) -> tuple[QueryAdapter, Mapping[str, Any], Mapping[str, torch.Tensor]]:
    core.deterministic_setup(seed)
    dimension = int(corpus.chosen_vectors.shape[1])
    model = QueryAdapter(
        int(corpus.facet_inputs.shape[2]), dimension, int(config["adapter"]["hidden_dimension"])
    )
    if initial_state is not None:
        model.load_state_dict(initial_state)
    initial = {key: value.detach().clone() for key, value in model.state_dict().items()}
    if not torch.count_nonzero(model.output.weight).item() == 0 or not torch.count_nonzero(model.output.bias).item() == 0:
        raise IntegrityError("Adapter output layer is not zero initialized")
    chosen = corpus.chosen_vectors.copy()
    rejected = corpus.rejected_vectors.copy()
    reversed_rows = np.zeros(len(chosen), dtype=np.bool_)
    if shuffled_direction:
        grouped: dict[int, list[int]] = defaultdict(list)
        for row, user_id in enumerate(corpus.user_ids):
            grouped[int(user_id)].append(row)
        for _user_id, rows in grouped.items():
            # Global cap storage is round-aware, so ascending preserved row
            # index within a user is exactly that user's registered pair-cap
            # hash order.  No second control-specific hash is permitted.
            ordered = sorted(rows)
            for position, row in enumerate(ordered):
                if position % 2 == 0:
                    reversed_rows[row] = True
        temporary = chosen[reversed_rows].copy()
        chosen[reversed_rows] = rejected[reversed_rows]
        rejected[reversed_rows] = temporary
    weights = corpus.macro_weights if weighting == "user_facet_macro" else np.ones(len(chosen), dtype=np.float32)
    if weighting not in {"user_facet_macro", "pair_micro"}:
        raise ValueError(weighting)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(config["alignment"]["learning_rate"]),
        weight_decay=float(config["alignment"]["weight_decay"]),
    )
    rows_by_user: dict[int, np.ndarray] = {}
    for user_id in sorted(set(map(int, corpus.user_ids))):
        rows_by_user[user_id] = np.flatnonzero(corpus.user_ids == user_id)
    group_size = int(config["alignment"]["user_group_size"])
    trace: list[float] = []
    model.train()
    for epoch in range(int(config["alignment"]["epochs"])):
        user_order = sorted(
            rows_by_user,
            key=lambda user_id: (
                hashlib.sha256(
                    f"20263116:train:{seed}:{epoch}:{user_id}".encode("ascii")
                ).hexdigest(),
                user_id,
            ),
        )
        losses: list[float] = []
        for start in range(0, len(user_order), group_size):
            group_users = user_order[start : start + group_size]
            rows = np.concatenate([rows_by_user[user_id] for user_id in group_users])
            inputs_t = torch.from_numpy(corpus.facet_inputs[rows])
            mask_t = torch.from_numpy(corpus.facet_mask[rows])
            chosen_t = torch.from_numpy(chosen[rows])
            rejected_t = torch.from_numpy(rejected[rows])
            queries = _adapter_queries_torch(
                model,
                inputs_t,
                mask_t,
                dimension,
                float(config["adapter"]["query_displacement_bound"]),
            )
            chosen_scores = torch.sum(queries * chosen_t.unsqueeze(1), dim=2)
            rejected_scores = torch.sum(queries * rejected_t.unsqueeze(1), dim=2)
            invalid = ~mask_t
            chosen_scores = chosen_scores.masked_fill(invalid, -torch.inf)
            rejected_scores = rejected_scores.masked_fill(invalid, -torch.inf)
            delta = torch.max(chosen_scores, dim=1).values - torch.max(rejected_scores, dim=1).values
            per_pair = F.softplus(float(config["alignment"]["beta"]) * (float(margin) - delta))
            weight_t = torch.from_numpy(weights[rows])
            loss = torch.sum(per_pair * weight_t) / torch.clamp(torch.sum(weight_t), min=1e-12)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), float(config["alignment"]["gradient_clip_norm"]))
            optimizer.step()
            losses.append(float(loss.detach()))
        trace.append(float(np.mean(losses)))
    model.eval()
    state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    return model, {
        "seed": seed,
        "margin": float(margin),
        "weighting": weighting,
        "shuffled_direction": shuffled_direction,
        "reversed_pairs": int(np.sum(reversed_rows)),
        "pairs": len(chosen),
        "pair_identity_sha256": core.sha256_bytes(core.canonical_json_bytes(corpus.pair_keys)),
        "epoch_mean_losses": trace,
        "reference_model_used": False,
        "output_layer_zero_initialized": True,
    }, state


def search_semantic_novel(
    semantic_index: Any,
    queries: np.ndarray,
    blocked_history: frozenset[int],
    collaborative: Sequence[int],
    config: Mapping[str, Any],
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    """Fixed-depth batched FAISS retrieval with deterministic quotas/backfill."""
    query_matrix = np.ascontiguousarray(queries, dtype=np.float32)
    if query_matrix.ndim != 2 or len(query_matrix) not in {1, 2}:
        raise IntegrityError("Semantic retrieval requires one or two facet queries")
    depth = int(config["retrieval"]["semantic_search_depth_per_query"])
    if depth > int(semantic_index.ntotal):
        raise IntegrityError("The fixed semantic search depth exceeds catalog size")
    _scores, raw_indices = semantic_index.search(query_matrix, depth)
    raw_overlap = (
        len(set(map(int, raw_indices[0])) & set(map(int, raw_indices[1])))
        if len(query_matrix) == 2
        else 0
    )
    forbidden = set(blocked_history) | set(map(int, collaborative))
    rows: list[list[int]] = []
    for facet in range(len(query_matrix)):
        candidates: list[int] = []
        local_seen: set[int] = set()
        for raw_item in raw_indices[facet]:
            item = int(raw_item)
            if item < 0 or item in forbidden or item in local_seen:
                continue
            candidates.append(item)
            local_seen.add(item)
        rows.append(candidates)
    original_rows = [list(row) for row in rows]
    eligible_overlap = 0
    duplicates_removed = 0
    if len(rows) == 2:
        lower_owner = set(rows[0])
        eligible_overlap = len(lower_owner & set(rows[1]))
        rows[1] = [item for item in rows[1] if item not in lower_owner]
        duplicates_removed = len(original_rows[1]) - len(rows[1])
        if duplicates_removed != eligible_overlap:
            raise IntegrityError("Cross-facet duplicate ownership accounting failed")
    selected: list[int] = []
    selected_set: set[int] = set()
    selected_owner: list[int] = []
    pointers = [0 for _ in rows]

    def take(facet: int) -> bool:
        while pointers[facet] < len(rows[facet]):
            item = rows[facet][pointers[facet]]
            pointers[facet] += 1
            if item in selected_set:
                continue
            selected.append(item)
            selected_set.add(item)
            selected_owner.append(facet)
            return True
        return False

    if len(rows) == 1:
        while len(selected) < 200 and take(0):
            pass
        quotas = (len(selected),)
    else:
        quota_counts = [0, 0]
        for facet in range(2):
            while quota_counts[facet] < 100:
                if not take(facet):
                    break
                quota_counts[facet] += 1
        # Only the same two depth-700 rows may backfill; canonical round robin.
        cursor = 0
        exhausted_rounds = 0
        while len(selected) < 200:
            facet = cursor % 2
            cursor += 1
            if take(facet):
                quota_counts[facet] += 1
                exhausted_rounds = 0
            else:
                exhausted_rounds += 1
                if exhausted_rounds >= 2:
                    break
        quotas = tuple(quota_counts)
    if len(selected) != 200:
        raise IntegrityError(
            f"Fixed semantic rows yield {len(selected)} BPR-novel unseen items, not 200"
        )
    if len(selected_set) != 200 or selected_set & forbidden:
        raise IntegrityError("Semantic novelty/uniqueness contract failed")
    lower_owner_violations = 0
    if len(rows) == 2:
        # Every item owned/selected by facet 1 must be absent from facet 0's
        # eligible returned row, even if it occurred late in that row.
        facet1_owned = {
            item for item, owner in zip(selected, selected_owner, strict=True) if owner == 1
        }
        lower_owner_violations = len(facet1_owned & set(original_rows[0]))
        if lower_owner_violations:
            raise IntegrityError("Higher canonical facet claimed a lower-owned duplicate")
    diagnostics = (
        raw_overlap,
        eligible_overlap,
        duplicates_removed,
        lower_owner_violations,
        len(original_rows[0]),
        len(original_rows[1]) if len(original_rows) == 2 else 0,
    )
    return tuple(selected), quotas, diagnostics, tuple(selected_owner)


def search_collaborative_fixed(
    index: Any,
    query: np.ndarray,
    blocked_history: frozenset[int],
    config: Mapping[str, Any],
) -> tuple[int, ...]:
    depth = int(config["retrieval"]["collaborative_search_depth"])
    _scores, indices = index.search(
        np.ascontiguousarray(query.reshape(1, -1), dtype=np.float32), depth
    )
    selected: list[int] = []
    selected_set: set[int] = set()
    for raw_item in indices[0]:
        item = int(raw_item)
        if item < 0 or item in blocked_history or item in selected_set:
            continue
        selected.append(item)
        selected_set.add(item)
        if len(selected) == int(config["retrieval"]["collaborative_candidates_exact"]):
            break
    if len(selected) != 200:
        raise IntegrityError("The fixed depth-700 collaborative row exhausted before 200")
    return tuple(selected)


def retrieve_record(
    user_id: int,
    history: Sequence[Interaction],
    descriptor: FacetDescriptor,
    adapter: QueryAdapter | None,
    bpr: BPRArtifacts,
    collaborative_index: Any,
    semantic_vectors: np.ndarray,
    semantic_index: Any,
    movie_ids: Sequence[int],
    config: Mapping[str, Any],
    alpha: float | None,
) -> RetrievalRecord:
    queries = apply_adapter(
        descriptor, adapter, float(config["adapter"]["query_displacement_bound"])
    )
    collaborative_query = core.updated_bpr_query(bpr, user_id, history, config["bpr"])
    blocked = frozenset(event.item_index for event in history)
    collaborative = search_collaborative_fixed(
        collaborative_index,
        collaborative_query,
        blocked,
        config,
    )
    semantic, quota, retrieval_diagnostics, semantic_owners = search_semantic_novel(
        semantic_index, queries, blocked, collaborative, config
    )
    owner_counts = tuple(
        int(np.sum(np.asarray(semantic_owners, dtype=np.int8) == facet))
        for facet in range(len(quota))
    )
    if owner_counts != tuple(quota):
        raise IntegrityError("Per-item semantic ownership disagrees with quota accounting")
    union = (*collaborative, *semantic)
    if len(union) != 400 or len(set(union)) != 400 or set(union) & set(blocked):
        raise IntegrityError("Exact 200+200 unseen union contract failed")
    indices = np.asarray(union, dtype=np.int64)
    bpr_raw = np.asarray(bpr.item_vectors[indices] @ collaborative_query, dtype=np.float32)
    facet_scores = np.asarray(semantic_vectors[indices] @ queries.T, dtype=np.float32)
    winners = np.argmax(facet_scores, axis=1).astype(np.int8)
    semantic_raw = facet_scores[np.arange(len(indices)), winners].astype(np.float32)
    if alpha is None:
        combined = np.zeros(400, dtype=np.float32)
        ranking = union
    else:
        combined = np.asarray(
            float(alpha) * _safe_quantile_normalize(bpr_raw)
            + (1.0 - float(alpha)) * _safe_quantile_normalize(semantic_raw),
            dtype=np.float32,
        )
        ranking = rank_descending(union, combined, movie_ids)
    return RetrievalRecord(
        collaborative=tuple(collaborative),
        semantic=tuple(semantic),
        union=tuple(union),
        ranking=tuple(ranking),
        scores=combined,
        raw_bpr_scores=bpr_raw,
        raw_semantic_scores=semantic_raw,
        facet_queries=queries,
        facet_winners=winners,
        quota_utilization=quota,
        retrieval_diagnostics=retrieval_diagnostics,
        semantic_owners=semantic_owners,
    )


@dataclass(frozen=True)
class RawManifest:
    user_ids: np.ndarray
    candidates: np.ndarray
    bpr_scores: np.ndarray
    semantic_scores: np.ndarray
    rankings: np.ndarray
    final_scores: np.ndarray
    facet_counts: np.ndarray
    quota_utilization: np.ndarray
    retrieval_diagnostics: np.ndarray
    semantic_owners: np.ndarray
    histories_sha256: str
    alpha_grid: np.ndarray
    alpha_grid_rankings: np.ndarray


def method_query_specs(
    full_descriptor: FacetDescriptor,
    single_descriptor: FacetDescriptor,
    adapters: Mapping[str, QueryAdapter],
) -> Mapping[str, tuple[FacetDescriptor, QueryAdapter | None]]:
    return {
        "raw_single_centroid_hybrid": (single_descriptor, None),
        "raw_multi_facet": (full_descriptor, None),
        "single_query_aligned": (single_descriptor, adapters["single_query_aligned"]),
        "multi_facet_zero_margin": (full_descriptor, adapters["multi_facet_zero_margin"]),
        "multi_facet_shuffled_direction": (full_descriptor, adapters["multi_facet_shuffled_direction"]),
        "multi_facet_pair_micro": (full_descriptor, adapters["multi_facet_pair_micro"]),
        "facet_pref": (full_descriptor, adapters["facet_pref"]),
    }


def build_raw_manifest(
    splits: Sequence[UserSplit],
    stage: str,
    full_descriptors: Mapping[int, FacetDescriptor],
    single_descriptors: Mapping[int, FacetDescriptor],
    adapters: Mapping[str, QueryAdapter],
    bpr: BPRArtifacts,
    collaborative_index: Any,
    semantic_vectors: np.ndarray,
    semantic_index: Any,
    movie_ids: Sequence[int],
    config: Mapping[str, Any],
    alpha: float | None,
) -> RawManifest:
    if stage not in {"V", "T"}:
        raise ValueError(stage)
    user_ids = np.asarray([split.user_id for split in splits], dtype=np.int64)
    method_count, user_count = len(METHODS), len(splits)
    candidates = np.full((method_count, user_count, 400), -1, dtype=np.int32)
    bpr_scores = np.full((method_count, user_count, 400), np.nan, dtype=np.float32)
    semantic_scores = np.full_like(bpr_scores, np.nan)
    rankings = np.full_like(candidates, -1)
    final_scores = np.full_like(bpr_scores, np.nan)
    facet_counts = np.zeros((method_count, user_count), dtype=np.uint8)
    quota = np.zeros((method_count, user_count, 2), dtype=np.int16)
    retrieval_diagnostics = np.zeros(
        (method_count, user_count, len(RETRIEVAL_DIAGNOSTICS)), dtype=np.int16
    )
    semantic_owners = np.full((method_count, user_count, 200), -1, dtype=np.int8)
    history_hashes: list[Mapping[str, Any]] = []
    for user_row, split in enumerate(splits):
        history = (
            (*split.train, *split.alignment)
            if stage == "V"
            else (*split.train, *split.alignment, *split.validation)
        )
        history_hashes.append(
            {
                "user_id": split.user_id,
                "events": [
                    [event.item_index, event.rating, event.timestamp, event.ordinal]
                    for event in history
                ],
            }
        )
        collaborative_query = core.updated_bpr_query(bpr, split.user_id, history, config["bpr"])
        blocked = frozenset(event.item_index for event in history)
        collaborative = search_collaborative_fixed(
            collaborative_index,
            collaborative_query,
            blocked,
            config,
        )
        bpr_raw = np.asarray(
            bpr.item_vectors[np.asarray(collaborative, dtype=np.int64)] @ collaborative_query,
            dtype=np.float32,
        )
        bpr_ranking = rank_descending(collaborative, bpr_raw, movie_ids)
        candidates[0, user_row, :200] = collaborative
        bpr_scores[0, user_row, :200] = bpr_raw
        if alpha is not None:
            rankings[0, user_row, :200] = bpr_ranking
            final_scores[0, user_row, :200] = bpr_raw
        for method_index, method in enumerate(HYBRID_METHODS, start=1):
            descriptor, adapter = method_query_specs(
                full_descriptors[split.user_id], single_descriptors[split.user_id], adapters
            )[method]
            record = retrieve_record(
                split.user_id,
                history,
                descriptor,
                adapter,
                bpr,
                collaborative_index,
                semantic_vectors,
                semantic_index,
                movie_ids,
                config,
                alpha,
            )
            candidates[method_index, user_row] = record.union
            bpr_scores[method_index, user_row] = record.raw_bpr_scores
            semantic_scores[method_index, user_row] = record.raw_semantic_scores
            facet_counts[method_index, user_row] = record.facet_queries.shape[0]
            quota[method_index, user_row, : len(record.quota_utilization)] = record.quota_utilization
            retrieval_diagnostics[method_index, user_row] = record.retrieval_diagnostics
            semantic_owners[method_index, user_row] = record.semantic_owners
            if alpha is not None:
                rankings[method_index, user_row] = record.ranking
                final_scores[method_index, user_row] = record.scores
    raw = RawManifest(
        user_ids=user_ids,
        candidates=candidates,
        bpr_scores=bpr_scores,
        semantic_scores=semantic_scores,
        rankings=rankings,
        final_scores=final_scores,
        facet_counts=facet_counts,
        quota_utilization=quota,
        retrieval_diagnostics=retrieval_diagnostics,
        semantic_owners=semantic_owners,
        histories_sha256=core.sha256_bytes(core.canonical_json_bytes(history_hashes)),
        alpha_grid=np.asarray([], dtype=np.float32),
        alpha_grid_rankings=np.empty((0, method_count, user_count, 400), dtype=np.int32),
    )
    if stage == "V" and alpha is None:
        grid = np.asarray(config["ranking"]["alpha_validation_grid"], dtype=np.float32)
        grid_rankings = np.full((len(grid), method_count, user_count, 400), -1, dtype=np.int32)
        for grid_row, grid_alpha in enumerate(grid):
            fused = apply_fusion_to_manifest(raw, float(grid_alpha), movie_ids)
            grid_rankings[grid_row] = fused.rankings
        return RawManifest(
            **{**raw.__dict__, "alpha_grid": grid, "alpha_grid_rankings": grid_rankings}
        )
    return raw


def apply_fusion_to_manifest(
    manifest: RawManifest, alpha: float, movie_ids: Sequence[int]
) -> RawManifest:
    rankings = np.full_like(manifest.candidates, -1)
    scores = np.full_like(manifest.bpr_scores, np.nan)
    for method_index, method in enumerate(METHODS):
        for user_row in range(len(manifest.user_ids)):
            size = 200 if method == "selected_bpr" else 400
            items = manifest.candidates[method_index, user_row, :size]
            if np.any(items < 0):
                raise IntegrityError("Manifest contains a missing candidate")
            if method == "selected_bpr":
                combined = manifest.bpr_scores[method_index, user_row, :size]
            else:
                combined = np.asarray(
                    float(alpha) * _safe_quantile_normalize(manifest.bpr_scores[method_index, user_row, :size])
                    + (1.0 - float(alpha))
                    * _safe_quantile_normalize(manifest.semantic_scores[method_index, user_row, :size]),
                    dtype=np.float32,
                )
            ranking = rank_descending(items, combined, movie_ids)
            rankings[method_index, user_row, :size] = ranking
            scores[method_index, user_row, :size] = combined
    return RawManifest(
        user_ids=manifest.user_ids,
        candidates=manifest.candidates,
        bpr_scores=manifest.bpr_scores,
        semantic_scores=manifest.semantic_scores,
        rankings=rankings,
        final_scores=scores,
        facet_counts=manifest.facet_counts,
        quota_utilization=manifest.quota_utilization,
        retrieval_diagnostics=manifest.retrieval_diagnostics,
        semantic_owners=manifest.semantic_owners,
        histories_sha256=manifest.histories_sha256,
        alpha_grid=manifest.alpha_grid,
        alpha_grid_rankings=manifest.alpha_grid_rankings,
    )


def publish_manifest(
    path: Path,
    manifest: RawManifest,
    protocol_sha256: str,
    stage: str,
    seed: int,
    variant: str,
    target_opened: bool,
) -> str:
    payload = _npz_bytes(
        user_ids=manifest.user_ids,
        candidates=manifest.candidates,
        bpr_scores=manifest.bpr_scores,
        semantic_scores=manifest.semantic_scores,
        rankings=manifest.rankings,
        final_scores=manifest.final_scores,
        facet_counts=manifest.facet_counts,
        quota_utilization=manifest.quota_utilization,
        retrieval_diagnostics=manifest.retrieval_diagnostics,
        retrieval_diagnostic_names=np.asarray(RETRIEVAL_DIAGNOSTICS, dtype="U48"),
        semantic_owners=manifest.semantic_owners,
        alpha_grid=manifest.alpha_grid,
        alpha_grid_rankings=manifest.alpha_grid_rankings,
        methods=np.asarray(METHODS, dtype="U32"),
        protocol_sha256=np.asarray([protocol_sha256], dtype="U64"),
        stage=np.asarray([stage], dtype="U1"),
        seed=np.asarray([seed], dtype=np.int64),
        bpr_variant=np.asarray([variant], dtype="U16"),
        histories_sha256=np.asarray([manifest.histories_sha256], dtype="U64"),
        target_outcomes_opened=np.asarray([int(target_opened)], dtype=np.uint8),
    )
    core.publish_bytes_no_overwrite(path, payload)
    return core.sha256_file(path)


def binary_ndcg(ranking: Sequence[int], positives: frozenset[int], k: int = 10) -> float:
    return core.binary_ndcg(ranking, positives, k)


def recall_at_k(ranking: Sequence[int], positives: frozenset[int], k: int = 10) -> float:
    return core.recall_at_k(ranking, positives, k)


def select_bpr_and_alpha(
    validation_manifests: Mapping[int, Mapping[str, RawManifest]],
    splits: Sequence[UserSplit],
    config: Mapping[str, Any],
) -> tuple[str, float, Mapping[str, Any]]:
    """Open V relevance only after all alpha-grid manifests are durable."""
    split_by_user = {split.user_id: split for split in splits}
    bpr_records: dict[str, tuple[float, float]] = {}
    for variant in ("implicit", "rating_aware"):
        ndcg_values: list[float] = []
        recall_values: list[float] = []
        for seed in config["optimization_seeds"]:
            manifest = validation_manifests[int(seed)][variant]
            # BPR order is invariant to alpha; use the first preregistered grid row.
            ranking_array = manifest.alpha_grid_rankings[0, 0]
            for user_row, user_id in enumerate(manifest.user_ids):
                positives = frozenset(
                    event.item_index
                    for event in split_by_user[int(user_id)].validation
                    if event.rating >= int(config["dataset"]["positive_rating_min"])
                )
                if not positives:
                    raise IntegrityError("Eligibility promised a V positive item")
                ranking = ranking_array[user_row, :200]
                ndcg_values.append(binary_ndcg(ranking, positives, 10))
                recall_values.append(recall_at_k(ranking, positives, 10))
        bpr_records[variant] = (float(np.mean(ndcg_values)), float(np.mean(recall_values)))
    selected_variant = max(
        ("implicit", "rating_aware"),
        key=lambda variant: (
            bpr_records[variant][0],
            bpr_records[variant][1],
            1 if variant == "implicit" else 0,
        ),
    )
    alpha_records: dict[float, tuple[float, float]] = {}
    grid = [float(value) for value in config["ranking"]["alpha_validation_grid"]]
    for grid_row, alpha in enumerate(grid):
        ndcg_values = []
        recall_values = []
        for seed in config["optimization_seeds"]:
            manifest = validation_manifests[int(seed)][selected_variant]
            if not math.isclose(float(manifest.alpha_grid[grid_row]), alpha, abs_tol=1e-7):
                raise IntegrityError("Published alpha grid changed before selection")
            ranking_array = manifest.alpha_grid_rankings[grid_row, 1]
            for user_row, user_id in enumerate(manifest.user_ids):
                positives = frozenset(
                    event.item_index
                    for event in split_by_user[int(user_id)].validation
                    if event.rating >= int(config["dataset"]["positive_rating_min"])
                )
                ndcg_values.append(binary_ndcg(ranking_array[user_row], positives, 10))
                recall_values.append(recall_at_k(ranking_array[user_row], positives, 10))
        alpha_records[alpha] = (float(np.mean(ndcg_values)), float(np.mean(recall_values)))
    selected_alpha = max(
        grid,
        key=lambda alpha: (
            alpha_records[alpha][0], alpha_records[alpha][1], alpha
        ),
    )
    return selected_variant, selected_alpha, {
        "bpr_validation_user_seed_macro": {
            variant: {"ndcg_at_10": values[0], "recall_at_10": values[1]}
            for variant, values in bpr_records.items()
        },
        "alpha_validation_user_seed_macro": {
            str(alpha): {"ndcg_at_10": values[0], "recall_at_10": values[1]}
            for alpha, values in alpha_records.items()
        },
        "selected_bpr_variant": selected_variant,
        "selected_alpha": selected_alpha,
        "selection_used_V_relevance_only": True,
        "V_preference_used_for_selection": False,
    }


@dataclass(frozen=True)
class OutcomeArrays:
    user_ids: np.ndarray
    event_items: np.ndarray
    event_ratings: np.ndarray
    event_counts: np.ndarray
    pair_chosen: np.ndarray
    pair_rejected: np.ndarray
    pair_counts: np.ndarray
    prefix_items: np.ndarray
    prefix_counts: np.ndarray
    total_pairs: int
    pair_bearing_users: int


def build_outcome_arrays(
    splits: Sequence[UserSplit],
    block: str,
    movie_ids: Sequence[int],
    config: Mapping[str, Any],
) -> OutcomeArrays:
    if block not in {"V", "T"}:
        raise ValueError(block)
    events_by_user = [split.validation if block == "V" else split.test for split in splits]
    prefixes = [
        (*split.train, *split.alignment)
        if block == "V"
        else (*split.train, *split.alignment, *split.validation)
        for split in splits
    ]
    maximum_events = max(map(len, events_by_user))
    maximum_prefix = max(map(len, prefixes))
    maximum_pairs = (
        int(config["power_audit"]["maximum_validation_pairs_per_user"])
        if block == "V"
        else int(config["evaluation"]["maximum_test_pairs_per_user"])
    )
    hash_seed = int(
        str(
            config["power_audit"]["validation_pair_hash_format"]
            if block == "V"
            else config["evaluation"]["test_pair_hash_format"]
        ).split(":", 1)[0]
    )
    event_items = np.full((len(splits), maximum_events), -1, dtype=np.int32)
    event_ratings = np.full((len(splits), maximum_events), -1, dtype=np.int8)
    event_counts = np.zeros(len(splits), dtype=np.int16)
    pair_chosen = np.full((len(splits), maximum_pairs), -1, dtype=np.int32)
    pair_rejected = np.full_like(pair_chosen, -1)
    pair_counts = np.zeros(len(splits), dtype=np.int16)
    prefix_items = np.full((len(splits), maximum_prefix), -1, dtype=np.int32)
    prefix_counts = np.zeros(len(splits), dtype=np.int16)
    for row, (split, events, prefix) in enumerate(zip(splits, events_by_user, prefixes, strict=True)):
        event_counts[row] = len(events)
        event_items[row, : len(events)] = [event.item_index for event in events]
        event_ratings[row, : len(events)] = [event.rating for event in events]
        prefix_counts[row] = len(prefix)
        prefix_items[row, : len(prefix)] = [event.item_index for event in prefix]
        pairs, _raw = natural_pairs(
            events,
            int(config["dataset"]["preference_pair_minimum_rating_gap"]),
            maximum_pairs,
            hash_seed,
            split.user_id,
            movie_ids,
        )
        pair_counts[row] = len(pairs)
        if pairs:
            pair_chosen[row, : len(pairs)] = [pair[0] for pair in pairs]
            pair_rejected[row, : len(pairs)] = [pair[1] for pair in pairs]
    return OutcomeArrays(
        user_ids=np.asarray([split.user_id for split in splits], dtype=np.int64),
        event_items=event_items,
        event_ratings=event_ratings,
        event_counts=event_counts,
        pair_chosen=pair_chosen,
        pair_rejected=pair_rejected,
        pair_counts=pair_counts,
        prefix_items=prefix_items,
        prefix_counts=prefix_counts,
        total_pairs=int(np.sum(pair_counts)),
        pair_bearing_users=int(np.sum(pair_counts > 0)),
    )


def evaluate_manifest(
    manifest: RawManifest,
    outcomes: OutcomeArrays,
    config: Mapping[str, Any],
) -> tuple[np.ndarray, Mapping[str, int]]:
    if not np.array_equal(manifest.user_ids, outcomes.user_ids):
        raise IntegrityError("Manifest/outcome user order mismatch")
    result = np.full((len(METHODS), len(outcomes.user_ids), len(METRICS)), np.nan, dtype=np.float64)
    metric_index = {name: index for index, name in enumerate(METRICS)}
    common_support = 0
    changed_outcomes = 0
    pair_rows = 0
    for user_row in range(len(outcomes.user_ids)):
        event_count = int(outcomes.event_counts[user_row])
        event_items = outcomes.event_items[user_row, :event_count]
        ratings = outcomes.event_ratings[user_row, :event_count]
        positives = frozenset(
            int(item) for item, rating in zip(event_items, ratings, strict=True)
            if int(rating) >= int(config["dataset"]["positive_rating_min"])
        )
        if not positives:
            raise IntegrityError("Fixed relevance cohort contains a missing positive set")
        low = frozenset(
            int(item) for item, rating in zip(event_items, ratings, strict=True)
            if int(rating) <= int(config["dataset"]["dislike_rating_max"])
        )
        pair_count = int(outcomes.pair_counts[user_row])
        chosen = outcomes.pair_chosen[user_row, :pair_count]
        rejected = outcomes.pair_rejected[user_row, :pair_count]
        pair_values_by_method: dict[str, np.ndarray] = {}
        candidate_sets: dict[str, set[int]] = {}
        for method_index, method in enumerate(METHODS):
            size = 200 if method == "selected_bpr" else 400
            candidates = tuple(map(int, manifest.candidates[method_index, user_row, :size]))
            ranking = tuple(map(int, manifest.rankings[method_index, user_row, :size]))
            if len(set(candidates)) != size or any(item < 0 for item in candidates):
                raise IntegrityError("Candidate manifest violates its exact size")
            if set(candidates) != set(ranking):
                raise IntegrityError("Ranking is not a permutation of candidates")
            candidate_set = set(candidates)
            candidate_sets[method] = candidate_set
            top10 = ranking[:10]
            result[method_index, user_row, metric_index["ndcg_at_10"]] = binary_ndcg(ranking, positives, 10)
            result[method_index, user_row, metric_index["recall_at_10"]] = recall_at_k(ranking, positives, 10)
            result[method_index, user_row, metric_index["low_rating_intrusion_at_10"]] = sum(item in low for item in top10) / 10.0
            result[method_index, user_row, metric_index["positive_union_recall"]] = len(candidate_set & positives) / len(positives)
            if pair_count:
                support = np.asarray(
                    [int(int(c) in candidate_set and int(r) in candidate_set) for c, r in zip(chosen, rejected, strict=True)],
                    dtype=np.float64,
                )
                rank10 = {item: position for position, item in enumerate(top10, start=1)}
                pair_values = np.asarray(
                    [int(rank10.get(int(c), 11) < rank10.get(int(r), 11)) for c, r in zip(chosen, rejected, strict=True)],
                    dtype=np.float64,
                )
                pair_values_by_method[method] = pair_values
                result[method_index, user_row, metric_index["pair_support"]] = float(np.mean(support))
                result[method_index, user_row, metric_index["spce_at_10"]] = float(np.mean(pair_values))
        if pair_count:
            pair_rows += pair_count
            facet_set = candidate_sets["facet_pref"]
            baseline_set = candidate_sets["raw_single_centroid_hybrid"]
            common_support += sum(
                int(int(c) in facet_set and int(r) in facet_set and int(c) in baseline_set and int(r) in baseline_set)
                for c, r in zip(chosen, rejected, strict=True)
            )
            changed_outcomes += int(
                np.sum(pair_values_by_method["facet_pref"] != pair_values_by_method["raw_single_centroid_hybrid"])
            )
    if not np.all(np.isfinite(result[:, :, 2:])):
        raise IntegrityError("A fixed relevance/intrusion metric is missing or nonfinite")
    pair_rows_mask = outcomes.pair_counts > 0
    if not np.all(np.isfinite(result[:, pair_rows_mask, :2])):
        raise IntegrityError("A fixed pair-cohort metric is missing or nonfinite")
    return result, {
        "common_support_count": common_support,
        "changed_outcome_count": changed_outcomes,
        "fixed_pair_rows": pair_rows,
    }


def paired_user_bootstrap(
    differences: np.ndarray,
    draws: int,
    alpha: float,
    seed: int,
) -> Mapping[str, float]:
    values = np.asarray(differences, dtype=np.float64)
    if values.ndim != 1 or not len(values) or not np.all(np.isfinite(values)):
        raise IntegrityError("Bootstrap differences are empty or nonfinite")
    rng = np.random.default_rng(seed)
    means = np.empty(draws, dtype=np.float64)
    chunk = 256
    for start in range(0, draws, chunk):
        count = min(chunk, draws - start)
        indices = rng.integers(0, len(values), size=(count, len(values)))
        means[start : start + count] = np.mean(values[indices], axis=1)
    lower, upper = np.quantile(means, [alpha / 2.0, 1.0 - alpha / 2.0])
    return {
        "point": float(np.mean(values)),
        "lower": float(lower),
        "upper": float(upper),
        "users": int(len(values)),
        "draws": int(draws),
        "seed": int(seed),
    }


def simulate_power(
    seed_averaged_difference: np.ndarray,
    config: Mapping[str, Any],
    seed: int,
) -> tuple[np.ndarray, float]:
    power = config["power_audit"]
    differences = np.asarray(seed_averaged_difference, dtype=np.float64)
    if differences.ndim != 1 or not len(differences):
        raise IntegrityError("Validation pair cohort is empty for the fixed power audit")
    if not np.all(np.isfinite(differences)):
        raise IntegrityError("Power-audit differences contain nonfinite values")
    centered = differences - float(np.mean(differences)) + float(power["alternative_delta"])
    rng = np.random.default_rng(seed)
    experiments = int(power["simulated_experiments"])
    sample_users = int(power["sample_users_with_replacement"])
    inner_draws = int(power["inner_bootstrap_draws"])
    alpha = float(power["alpha"])
    lower_bounds = np.empty(experiments, dtype=np.float64)
    for experiment in range(experiments):
        outer = centered[rng.integers(0, len(centered), size=sample_users)]
        inner_indices = rng.integers(
            0, sample_users, size=(inner_draws, sample_users)
        )
        inner_means = np.mean(outer[inner_indices], axis=1)
        lower_bounds[experiment] = float(np.quantile(inner_means, alpha / 2.0))
    probability = float(np.mean(lower_bounds > 0.0))
    return lower_bounds, probability


def run_validation_power_audit(
    fused_validation: Mapping[int, RawManifest],
    outcomes: OutcomeArrays,
    config: Mapping[str, Any],
) -> tuple[Mapping[str, Any], np.ndarray, np.ndarray, np.ndarray]:
    metrics_by_seed: list[np.ndarray] = []
    top10_by_seed: list[np.ndarray] = []
    for seed in config["optimization_seeds"]:
        manifest = fused_validation[int(seed)]
        metrics, _diagnostics = evaluate_manifest(manifest, outcomes, config)
        metrics_by_seed.append(metrics)
        top10_by_seed.append(manifest.rankings[:, :, :10])
    metrics = np.stack(metrics_by_seed).astype(np.float64)
    top10 = np.stack(top10_by_seed).astype(np.int32)
    pair_users = outcomes.pair_counts > 0
    spce_index = METRICS.index("spce_at_10")
    method_index = {method: index for index, method in enumerate(METHODS)}
    probabilities: dict[str, float] = {}
    lower_bounds: list[np.ndarray] = []
    differences: list[np.ndarray] = []
    comparator_order = ("raw_single_centroid_hybrid", "selected_bpr")
    if not np.any(pair_users):
        experiments = int(config["power_audit"]["simulated_experiments"])
        return {
            "passed": False,
            "probability_lower_bound_above_zero": {
                comparator: 0.0 for comparator in comparator_order
            },
            "minimum_probability": float(
                config["power_audit"]["minimum_probability_lower_bound_above_zero"]
            ),
            "pair_bearing_validation_users": 0,
            "comparators": list(comparator_order),
            "choices_changed": False,
            "failure_reason": "empty_validation_preference_pair_cohort",
        }, np.empty((2, 0), dtype=np.float64), np.full(
            (2, experiments), -np.inf, dtype=np.float64
        ), top10
    for comparator in comparator_order:
        per_user = np.mean(
            metrics[:, method_index["facet_pref"], :, spce_index]
            - metrics[:, method_index[comparator], :, spce_index],
            axis=0,
        )[pair_users]
        seed = int(config["power_audit"]["comparison_seeds"][comparator])
        bounds, probability = simulate_power(per_user, config, seed)
        differences.append(per_user)
        lower_bounds.append(bounds)
        probabilities[comparator] = probability
    threshold = float(config["power_audit"]["minimum_probability_lower_bound_above_zero"])
    passed = all(probabilities[comparator] >= threshold for comparator in comparator_order)
    return {
        "passed": bool(passed),
        "probability_lower_bound_above_zero": probabilities,
        "minimum_probability": threshold,
        "pair_bearing_validation_users": int(np.sum(pair_users)),
        "comparators": list(comparator_order),
        "choices_changed": False,
    }, np.stack(differences), np.stack(lower_bounds), top10


def candidate_invariants(
    candidates: np.ndarray,
    prefix_items: np.ndarray,
    prefix_counts: np.ndarray,
    retrieval_diagnostics: np.ndarray | None = None,
) -> Mapping[str, Any]:
    values = np.asarray(candidates)
    if values.ndim != 4 or values.shape[1] != len(METHODS) or values.shape[3] != 400:
        raise IntegrityError("Candidate raw array shape changed")
    violations = {
        "bpr_size_or_padding": 0,
        "hybrid_size": 0,
        "hybrid_duplicate": 0,
        "prefix_seen": 0,
        "semantic_bpr_overlap": 0,
        "hybrid_collaborative_branch_mismatch": 0,
        "lower_facet_ownership": 0,
        "retrieval_diagnostic_accounting": 0,
    }
    for seed_row in range(values.shape[0]):
        for user_row in range(values.shape[2]):
            prefix = set(map(int, prefix_items[user_row, : int(prefix_counts[user_row])]))
            bpr = values[seed_row, 0, user_row]
            if np.any(bpr[:200] < 0) or np.any(bpr[200:] != -1) or len(set(map(int, bpr[:200]))) != 200:
                violations["bpr_size_or_padding"] += 1
            if set(map(int, bpr[:200])) & prefix:
                violations["prefix_seen"] += 1
            for method_row in range(1, len(METHODS)):
                union = values[seed_row, method_row, user_row]
                if np.any(union < 0) or len(union) != 400:
                    violations["hybrid_size"] += 1
                    continue
                if len(set(map(int, union))) != 400:
                    violations["hybrid_duplicate"] += 1
                if set(map(int, union)) & prefix:
                    violations["prefix_seen"] += 1
                if set(map(int, union[:200])) & set(map(int, union[200:])):
                    violations["semantic_bpr_overlap"] += 1
                if not np.array_equal(union[:200], bpr[:200]):
                    violations["hybrid_collaborative_branch_mismatch"] += 1
                if retrieval_diagnostics is not None:
                    diagnostic = retrieval_diagnostics[seed_row, method_row, user_row]
                    if int(diagnostic[3]) != 0:
                        violations["lower_facet_ownership"] += 1
                    if int(diagnostic[1]) != int(diagnostic[2]):
                        violations["retrieval_diagnostic_accounting"] += 1
    return {
        "passed": not any(violations.values()),
        "violations": violations,
        "semantic_candidates_exact": 200,
        "collaborative_candidates_exact": 200,
        "hybrid_union_exact": 400,
    }


def evaluate_gates_from_arrays(
    metrics: np.ndarray,
    candidates: np.ndarray,
    outcomes: OutcomeArrays,
    alignment_diagnostics: Mapping[str, Any],
    power_audit: Mapping[str, Any],
    pair_diagnostics_by_seed: Sequence[Mapping[str, int]],
    latency_summary: Mapping[str, Any],
    immutable_and_provenance: bool,
    config: Mapping[str, Any],
    retrieval_diagnostics: np.ndarray | None = None,
) -> Mapping[str, Any]:
    """Pure G1--G8/internal-G9 replay used by runner and bound verifier."""
    values = np.asarray(metrics, dtype=np.float64)
    if values.shape[:2] != (3, len(METHODS)) or values.shape[2] != len(outcomes.user_ids):
        raise IntegrityError("Metric raw array shape changed")
    method = {name: index for index, name in enumerate(METHODS)}
    metric = {name: index for index, name in enumerate(METRICS)}
    pair_mask = outcomes.pair_counts > 0
    relevance_mask = np.ones(len(outcomes.user_ids), dtype=np.bool_)

    def comparison(proposal: str, baseline: str, metric_name: str) -> Mapping[str, float]:
        mask = pair_mask if metric_name in {"pair_support", "spce_at_10"} else relevance_mask
        delta = np.mean(
            values[:, method[proposal], :, metric[metric_name]]
            - values[:, method[baseline], :, metric[metric_name]],
            axis=0,
        )[mask]
        return paired_user_bootstrap(
            delta,
            int(config["evaluation"]["bootstrap_draws"]),
            float(config["evaluation"]["bootstrap_alpha"]),
            int(config["evaluation"]["bootstrap_seed"]),
        )

    baseline = "raw_single_centroid_hybrid"
    comparisons: dict[str, Mapping[str, float]] = {}
    for metric_name in METRICS:
        comparisons[f"facet_pref_vs_hybrid__{metric_name}"] = comparison(
            "facet_pref", baseline, metric_name
        )
    comparisons["facet_pref_vs_bpr__spce_at_10"] = comparison(
        "facet_pref", "selected_bpr", "spce_at_10"
    )
    invariant = candidate_invariants(
        candidates,
        outcomes.prefix_items,
        outcomes.prefix_counts,
        retrieval_diagnostics,
    )
    g1 = bool(invariant["passed"] and immutable_and_provenance)
    g2_pair = comparisons["facet_pref_vs_hybrid__pair_support"]
    g2_recall = comparisons["facet_pref_vs_hybrid__positive_union_recall"]
    g2 = bool(
        g2_pair["point"] >= float(config["promise_gate"]["G2"]["minimum_pair_support_point_gain"])
        and g2_pair["lower"] > 0.0
        and g2_recall["point"] >= float(config["promise_gate"]["G2"]["minimum_positive_union_recall_point_gain"])
        and g2_recall["lower"] > 0.0
    )
    spce_hybrid = comparisons["facet_pref_vs_hybrid__spce_at_10"]
    spce_bpr = comparisons["facet_pref_vs_bpr__spce_at_10"]
    minimum_spce = float(config["promise_gate"]["G3"]["minimum_spce_at_10_point_gain_each"])
    g3 = bool(
        spce_hybrid["point"] >= minimum_spce and spce_hybrid["lower"] > 0.0
        and spce_bpr["point"] >= minimum_spce and spce_bpr["lower"] > 0.0
    )
    ndcg = comparisons["facet_pref_vs_hybrid__ndcg_at_10"]
    recall = comparisons["facet_pref_vs_hybrid__recall_at_10"]
    intrusion = comparisons["facet_pref_vs_hybrid__low_rating_intrusion_at_10"]
    g4_config = config["promise_gate"]["G4"]
    g4 = bool(
        ndcg["point"] >= float(g4_config["minimum_ndcg_at_10_point_delta"])
        and ndcg["lower"] > float(g4_config["minimum_ndcg_at_10_lower_bound_strict"])
        and recall["lower"] > float(g4_config["minimum_recall_at_10_lower_bound_strict"])
        and intrusion["upper"] <= float(g4_config["maximum_intrusion_at_10_increase_upper_bound"])
    )
    seed_average = np.mean(values, axis=0)
    control_evidence: dict[str, Mapping[str, float]] = {}
    g5 = True
    for control in CONTROL_METHODS:
        pair_delta = float(np.mean(seed_average[method["facet_pref"], pair_mask, metric["pair_support"]] - seed_average[method[control], pair_mask, metric["pair_support"]]))
        spce_delta = float(np.mean(seed_average[method["facet_pref"], pair_mask, metric["spce_at_10"]] - seed_average[method[control], pair_mask, metric["spce_at_10"]]))
        control_evidence[control] = {"pair_support_delta": pair_delta, "spce_at_10_delta": spce_delta}
        g5 = bool(g5 and pair_delta > 0.0 and spce_delta > 0.0)
    common_count = sum(int(row["common_support_count"]) for row in pair_diagnostics_by_seed)
    changed_count = sum(int(row["changed_outcome_count"]) for row in pair_diagnostics_by_seed)
    pair_rows = sum(int(row["fixed_pair_rows"]) for row in pair_diagnostics_by_seed)
    common_fraction = common_count / pair_rows if pair_rows else 0.0
    changed_fraction = changed_count / pair_rows if pair_rows else 0.0
    g6_config = config["promise_gate"]["G6"]
    g6 = bool(
        int(alignment_diagnostics["raw_natural_pairs"]) >= int(g6_config["minimum_R_natural_pairs"])
        and int(alignment_diagnostics["raw_pair_bearing_users"]) >= int(g6_config["minimum_R_pair_bearing_users"])
        and outcomes.total_pairs >= int(g6_config["minimum_T_fixed_pairs"])
        and outcomes.pair_bearing_users >= int(g6_config["minimum_T_pair_bearing_users"])
        and bool(power_audit["passed"])
        and common_fraction >= float(g6_config["minimum_common_pair_endpoint_cosupport"])
        and changed_fraction >= float(g6_config["minimum_changed_spce_pair_outcome_fraction"])
    )
    stable_seed_rows: list[Mapping[str, Any]] = []
    stable_count = 0
    for seed_row, seed in enumerate(config["optimization_seeds"]):
        deltas = {
            metric_name: float(np.mean(
                values[seed_row, method["facet_pref"], pair_mask if metric_name in {"pair_support", "spce_at_10"} else relevance_mask, metric[metric_name]]
                - values[seed_row, method[baseline], pair_mask if metric_name in {"pair_support", "spce_at_10"} else relevance_mask, metric[metric_name]]
            ))
            for metric_name in ("pair_support", "spce_at_10", "positive_union_recall", "ndcg_at_10")
        }
        passed = bool(
            deltas["pair_support"] > 0.0 and deltas["spce_at_10"] > 0.0
            and deltas["positive_union_recall"] > 0.0
            and deltas["ndcg_at_10"] >= float(config["promise_gate"]["G7"]["minimum_ndcg_at_10_delta"])
        )
        stable_count += int(passed)
        stable_seed_rows.append({"seed": int(seed), "passed": passed, **deltas})
    g7 = stable_count >= int(config["promise_gate"]["G7"]["minimum_stable_seeds"])
    g8 = bool(latency_summary["passed"])
    g9_internal = bool(immutable_and_provenance)
    gates = {"G1": g1, "G2": g2, "G3": g3, "G4": g4, "G5": g5, "G6": g6, "G7": g7, "G8": g8, "G9": g9_internal}
    return {
        "gates": gates,
        "runner_candidate_promising": bool(all(gates.values())),
        "PROMISING": False,
        "external_G9_replay_pending": True,
        "comparisons": comparisons,
        "control_evidence": control_evidence,
        "support_evidence": {
            "common_pair_endpoint_cosupport": common_fraction,
            "changed_spce_pair_outcome_fraction": changed_fraction,
            "T_fixed_pairs": outcomes.total_pairs,
            "T_pair_bearing_users": outcomes.pair_bearing_users,
        },
        "seed_stability": stable_seed_rows,
        "candidate_invariants": invariant,
        "latency": latency_summary,
    }


def benchmark_latency(
    splits: Sequence[UserSplit],
    adapters_by_seed: Mapping[int, Mapping[str, QueryAdapter]],
    bpr: BPRArtifacts,
    collaborative_index: Any,
    semantic_vectors: np.ndarray,
    semantic_index: Any,
    movie_ids: Sequence[int],
    alpha: float,
    config: Mapping[str, Any],
) -> tuple[np.ndarray, Mapping[str, Any]]:
    evaluation = config["evaluation"]
    ordered = sorted(splits, key=lambda split: split.user_id)
    measured_count = int(evaluation["latency_measured_users"])
    warmup_count = int(evaluation["latency_warmup_users"])
    if len(ordered) < measured_count or warmup_count > measured_count:
        raise IntegrityError("Latency cohort is unavailable")
    measured = ordered[:measured_count]
    repetitions = int(evaluation["latency_repetitions"])
    durations = np.zeros((3, 2, measured_count, repetitions), dtype=np.float64)

    def invoke(split: UserSplit, method_name: str, adapter: QueryAdapter | None) -> None:
        history = (*split.train, *split.alignment, *split.validation)
        descriptor = build_facet_descriptor(
            split.user_id,
            history,
            semantic_vectors,
            movie_ids,
            config,
            force_single=method_name == "raw_single_centroid_hybrid",
        )
        retrieve_record(
            split.user_id,
            history,
            descriptor,
            adapter,
            bpr,
            collaborative_index,
            semantic_vectors,
            semantic_index,
            movie_ids,
            config,
            alpha,
        )

    for seed_row, seed in enumerate(config["optimization_seeds"]):
        facet_adapter = adapters_by_seed[int(seed)]["facet_pref"]
        for split in measured[:warmup_count]:
            invoke(split, "raw_single_centroid_hybrid", None)
            invoke(split, "facet_pref", facet_adapter)
        for repetition in range(repetitions):
            order = (0, 1) if repetition % 2 == 0 else (1, 0)
            for user_row, split in enumerate(measured):
                for method_row in order:
                    started = time.perf_counter_ns()
                    if method_row == 0:
                        invoke(split, "raw_single_centroid_hybrid", None)
                    else:
                        invoke(split, "facet_pref", facet_adapter)
                    durations[seed_row, method_row, user_row, repetition] = (
                        time.perf_counter_ns() - started
                    ) / 1_000_000.0
    per_user_median = np.median(durations, axis=3)
    p95 = np.quantile(per_user_median, 0.95, axis=2)
    ratios = p95[:, 1] / np.maximum(p95[:, 0], 1e-12)
    worst_facet = float(np.max(p95[:, 1]))
    worst_ratio = float(np.max(ratios))
    maximum_ms = float(config["promise_gate"]["G8"]["maximum_worst_seed_p95_latency_ms"])
    maximum_ratio = float(config["promise_gate"]["G8"]["maximum_worst_seed_p95_latency_ratio"])
    return durations, {
        "methods": ["raw_single_centroid_hybrid", "facet_pref"],
        "seeds": list(map(int, config["optimization_seeds"])),
        "p95_ms_by_seed_method": p95.tolist(),
        "ratio_by_seed": ratios.tolist(),
        "worst_seed_facet_pref_p95_ms": worst_facet,
        "worst_seed_latency_ratio": worst_ratio,
        "maximum_ms": maximum_ms,
        "maximum_ratio": maximum_ratio,
        "passed": bool(worst_facet <= maximum_ms and worst_ratio <= maximum_ratio),
        "timed_users": measured_count,
        "warmup_users": warmup_count,
        "repetitions": repetitions,
        "reduction": "per-user median then user p95",
    }


def temporal_block_arrays(
    splits: Sequence[UserSplit],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    minimums = np.zeros((len(splits), 4), dtype=np.int64)
    maximums = np.zeros_like(minimums)
    counts = np.zeros((len(splits), 4), dtype=np.int16)
    for row, split in enumerate(splits):
        for block, events in enumerate(
            (split.train, split.alignment, split.validation, split.test)
        ):
            if not events:
                raise IntegrityError("A locked temporal block is empty")
            timestamps = [event.timestamp for event in events]
            minimums[row, block] = min(timestamps)
            maximums[row, block] = max(timestamps)
            counts[row, block] = len(events)
    if not np.all(maximums[:, :-1] < minimums[:, 1:]):
        raise IntegrityError("Strict temporal block order failed")
    return minimums, maximums, counts


def stack_test_manifests(
    manifests: Mapping[int, RawManifest], config: Mapping[str, Any]
) -> Mapping[str, np.ndarray]:
    ordered = [manifests[int(seed)] for seed in config["optimization_seeds"]]
    first_users = ordered[0].user_ids
    if any(not np.array_equal(manifest.user_ids, first_users) for manifest in ordered[1:]):
        raise IntegrityError("Seed manifests use different users")
    return {
        "user_ids": first_users,
        "candidates": np.stack([manifest.candidates for manifest in ordered]),
        "rankings": np.stack([manifest.rankings for manifest in ordered]),
        "bpr_scores": np.stack([manifest.bpr_scores for manifest in ordered]),
        "semantic_scores": np.stack([manifest.semantic_scores for manifest in ordered]),
        "final_scores": np.stack([manifest.final_scores for manifest in ordered]),
        "facet_counts": np.stack([manifest.facet_counts for manifest in ordered]),
        "quota_utilization": np.stack([manifest.quota_utilization for manifest in ordered]),
        "retrieval_diagnostics": np.stack(
            [manifest.retrieval_diagnostics for manifest in ordered]
        ),
        "semantic_owners": np.stack([manifest.semantic_owners for manifest in ordered]),
    }


def publish_raw_validation_power(
    path: Path,
    outcomes: OutcomeArrays,
    top10: np.ndarray,
    differences: np.ndarray,
    lower_bounds: np.ndarray,
    power_audit: Mapping[str, Any],
    corpus: PairCorpus,
    split_diagnostics: Mapping[str, Any],
    temporal: tuple[np.ndarray, np.ndarray, np.ndarray],
    movie_ids: Sequence[int],
    config: Mapping[str, Any],
    protocol_sha256: str,
    stage_times: Mapping[str, int],
    selection: Mapping[str, Any],
    validation_manifest_paths: Mapping[str, Path],
    splits: Sequence[UserSplit],
    pair_pool_path: Path,
) -> str:
    counts_map = corpus.diagnostics["uncapped_pair_counts_by_user"]
    alignment_counts = np.asarray(
        [int(counts_map[str(int(user_id))]) for user_id in outcomes.user_ids],
        dtype=np.int32,
    )
    probabilities = power_audit["probability_lower_bound_above_zero"]
    minimums, maximums, block_counts = temporal
    maximum_r_events = max(len(split.alignment) for split in splits)
    r_event_items = np.full((len(splits), maximum_r_events), -1, dtype=np.int32)
    r_event_ratings = np.full((len(splits), maximum_r_events), -1, dtype=np.int8)
    r_event_counts = np.zeros(len(splits), dtype=np.int16)
    for row, split in enumerate(splits):
        r_event_counts[row] = len(split.alignment)
        r_event_items[row, : len(split.alignment)] = [
            event.item_index for event in split.alignment
        ]
        r_event_ratings[row, : len(split.alignment)] = [
            event.rating for event in split.alignment
        ]
    payload = _npz_bytes(
        schema=np.asarray(["facet-pref-raw-validation-power-v1"], dtype="U48"),
        protocol_sha256=np.asarray([protocol_sha256], dtype="U64"),
        methods=np.asarray(METHODS, dtype="U40"),
        seeds=np.asarray(config["optimization_seeds"], dtype=np.int64),
        user_ids=outcomes.user_ids,
        movie_ids=np.asarray(movie_ids, dtype=np.int32),
        pair_chosen=outcomes.pair_chosen,
        pair_rejected=outcomes.pair_rejected,
        pair_counts=outcomes.pair_counts,
        validation_event_items=outcomes.event_items,
        validation_event_ratings=outcomes.event_ratings,
        validation_event_counts=outcomes.event_counts,
        prefix_items=outcomes.prefix_items,
        prefix_counts=outcomes.prefix_counts,
        top10=np.asarray(top10, dtype=np.int32),
        comparator_methods=np.asarray(
            ["raw_single_centroid_hybrid", "selected_bpr"], dtype="U40"
        ),
        seed_averaged_spce_differences=np.asarray(differences, dtype=np.float64),
        power_lower_bounds=np.asarray(lower_bounds, dtype=np.float64),
        power_pass_probability=np.asarray(
            [probabilities["raw_single_centroid_hybrid"], probabilities["selected_bpr"]],
            dtype=np.float64,
        ),
        power_passed=np.asarray([int(power_audit["passed"])], dtype=np.uint8),
        selected_bpr_variant=np.asarray([selection["selected_bpr_variant"]], dtype="U16"),
        selected_alpha=np.asarray([float(selection["selected_alpha"])], dtype=np.float32),
        validation_manifest_keys=np.asarray(list(validation_manifest_paths), dtype="U40"),
        validation_manifest_files=np.asarray(
            [validation_manifest_paths[key].name for key in validation_manifest_paths], dtype="U128"
        ),
        validation_manifest_sha256=np.asarray(
            [core.sha256_file(validation_manifest_paths[key]) for key in validation_manifest_paths], dtype="U64"
        ),
        alignment_uncapped_pair_counts_by_user=alignment_counts,
        R_event_items=r_event_items,
        R_event_ratings=r_event_ratings,
        R_event_counts=r_event_counts,
        alignment_selected_user_ids=corpus.user_ids,
        alignment_selected_chosen_items=corpus.chosen_items,
        alignment_selected_rejected_items=corpus.rejected_items,
        alignment_selected_assigned_facets=corpus.assigned_facets,
        R_pair_pool_file=np.asarray([pair_pool_path.name], dtype="U128"),
        R_pair_pool_sha256=np.asarray([core.sha256_file(pair_pool_path)], dtype="U64"),
        historical_caper_user_ids=np.asarray(split_diagnostics["caper_user_ids"], dtype=np.int64),
        historical_ravel_user_ids=np.asarray(split_diagnostics["ravel_user_ids"], dtype=np.int64),
        block_min_timestamps=minimums,
        block_max_timestamps=maximums,
        block_counts=block_counts,
        R_manifest_published_ns=np.asarray([stage_times["R_manifest_published_ns"]], dtype=np.int64),
        R_target_joined_ns=np.asarray([stage_times["R_target_joined_ns"]], dtype=np.int64),
        V_manifest_published_ns=np.asarray([stage_times["V_manifest_published_ns"]], dtype=np.int64),
        V_relevance_joined_ns=np.asarray([stage_times["V_relevance_joined_ns"]], dtype=np.int64),
        choices_frozen_ns=np.asarray([stage_times["choices_frozen_ns"]], dtype=np.int64),
        V_preference_joined_ns=np.asarray([stage_times["V_preference_joined_ns"]], dtype=np.int64),
        T_opened=np.asarray([0], dtype=np.uint8),
    )
    core.publish_bytes_no_overwrite(path, payload)
    return core.sha256_file(path)


def publish_raw_test_arrays(
    path: Path,
    stacked: Mapping[str, np.ndarray],
    metrics: np.ndarray,
    outcomes: OutcomeArrays,
    pair_diagnostics: Sequence[Mapping[str, int]],
    split_diagnostics: Mapping[str, Any],
    temporal: tuple[np.ndarray, np.ndarray, np.ndarray],
    movie_ids: Sequence[int],
    config: Mapping[str, Any],
    protocol_sha256: str,
    stage_times: Mapping[str, int],
    selected_alpha: float,
    selected_bpr_variant: str,
    test_manifest_paths: Mapping[str, Path],
) -> str:
    minimums, maximums, block_counts = temporal
    payload = _npz_bytes(
        schema=np.asarray(["facet-pref-raw-test-v1"], dtype="U40"),
        protocol_sha256=np.asarray([protocol_sha256], dtype="U64"),
        methods=np.asarray(METHODS, dtype="U40"),
        metric_names=np.asarray(METRICS, dtype="U40"),
        seeds=np.asarray(config["optimization_seeds"], dtype=np.int64),
        user_ids=outcomes.user_ids,
        movie_ids=np.asarray(movie_ids, dtype=np.int32),
        candidates=stacked["candidates"],
        rankings=stacked["rankings"],
        bpr_scores=stacked["bpr_scores"],
        semantic_scores=stacked["semantic_scores"],
        final_scores=stacked["final_scores"],
        facet_counts=stacked["facet_counts"],
        quota_utilization=stacked["quota_utilization"],
        retrieval_diagnostics=stacked["retrieval_diagnostics"],
        retrieval_diagnostic_names=np.asarray(RETRIEVAL_DIAGNOSTICS, dtype="U48"),
        semantic_owners=stacked["semantic_owners"],
        metrics=np.asarray(metrics, dtype=np.float64),
        test_event_items=outcomes.event_items,
        test_event_ratings=outcomes.event_ratings,
        test_event_counts=outcomes.event_counts,
        pair_chosen=outcomes.pair_chosen,
        pair_rejected=outcomes.pair_rejected,
        pair_counts=outcomes.pair_counts,
        prefix_items=outcomes.prefix_items,
        prefix_counts=outcomes.prefix_counts,
        common_support_counts=np.asarray(
            [row["common_support_count"] for row in pair_diagnostics], dtype=np.int64
        ),
        changed_outcome_counts=np.asarray(
            [row["changed_outcome_count"] for row in pair_diagnostics], dtype=np.int64
        ),
        total_pair_rows=np.asarray(
            [row["fixed_pair_rows"] for row in pair_diagnostics], dtype=np.int64
        ),
        historical_caper_user_ids=np.asarray(split_diagnostics["caper_user_ids"], dtype=np.int64),
        historical_ravel_user_ids=np.asarray(split_diagnostics["ravel_user_ids"], dtype=np.int64),
        block_min_timestamps=minimums,
        block_max_timestamps=maximums,
        block_counts=block_counts,
        R_manifest_published_ns=np.asarray([stage_times["R_manifest_published_ns"]], dtype=np.int64),
        R_target_joined_ns=np.asarray([stage_times["R_target_joined_ns"]], dtype=np.int64),
        V_manifest_published_ns=np.asarray([stage_times["V_manifest_published_ns"]], dtype=np.int64),
        V_relevance_joined_ns=np.asarray([stage_times["V_relevance_joined_ns"]], dtype=np.int64),
        choices_frozen_ns=np.asarray([stage_times["choices_frozen_ns"]], dtype=np.int64),
        V_preference_joined_ns=np.asarray([stage_times["V_preference_joined_ns"]], dtype=np.int64),
        T_manifest_published_ns=np.asarray([stage_times["T_manifest_published_ns"]], dtype=np.int64),
        T_target_joined_ns=np.asarray([stage_times["T_target_joined_ns"]], dtype=np.int64),
        T_opened=np.asarray([1], dtype=np.uint8),
        selected_alpha=np.asarray([float(selected_alpha)], dtype=np.float32),
        selected_bpr_variant=np.asarray([str(selected_bpr_variant)], dtype="U16"),
        test_manifest_seed_keys=np.asarray(list(test_manifest_paths), dtype="U24"),
        test_manifest_files=np.asarray(
            [test_manifest_paths[key].name for key in test_manifest_paths], dtype="U128"
        ),
        test_manifest_sha256=np.asarray(
            [core.sha256_file(test_manifest_paths[key]) for key in test_manifest_paths], dtype="U64"
        ),
    )
    core.publish_bytes_no_overwrite(path, payload)
    return core.sha256_file(path)


def publish_latency_arrays(
    path: Path,
    durations: np.ndarray,
    summary: Mapping[str, Any],
    protocol_sha256: str,
    config: Mapping[str, Any],
) -> str:
    core.publish_bytes_no_overwrite(
        path,
        _npz_bytes(
            schema=np.asarray(["facet-pref-latency-v1"], dtype="U32"),
            protocol_sha256=np.asarray([protocol_sha256], dtype="U64"),
            seeds=np.asarray(config["optimization_seeds"], dtype=np.int64),
            methods=np.asarray(summary["methods"], dtype="U40"),
            durations_ms=np.asarray(durations, dtype=np.float64),
            p95_ms_by_seed_method=np.asarray(summary["p95_ms_by_seed_method"], dtype=np.float64),
            ratio_by_seed=np.asarray(summary["ratio_by_seed"], dtype=np.float64),
        ),
    )
    return core.sha256_file(path)


def _adapter_initial_state(config: Mapping[str, Any], seed: int) -> Mapping[str, torch.Tensor]:
    core.deterministic_setup(seed)
    model = QueryAdapter(
        int(config["adapter"]["input_dimension"]),
        int(config["adapter"]["output_dimension"]),
        int(config["adapter"]["hidden_dimension"]),
    )
    return {key: value.detach().clone() for key, value in model.state_dict().items()}


def adapter_memory_sha256(model: QueryAdapter) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        array = np.ascontiguousarray(tensor.detach().cpu().numpy())
        digest.update(name.encode("utf-8"))
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(core.canonical_json_bytes(list(array.shape)))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _matrix_index_after_records(records: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    result: dict[str, Any] = {}
    for record in records:
        name = str(record["name"])
        matrix_after_file = core.sha256_file(record["matrix_path"])
        matrix_after_memory = core.sha256_bytes(record["matrix"].tobytes(order="C"))
        index_after_file = core.sha256_file(record["index_path"])
        index_after_memory = core.sha256_bytes(core.serialize_faiss(record["index"]))
        result[name] = {
            "matrix_file": Path(record["matrix_path"]).name,
            "index_file": Path(record["index_path"]).name,
            "matrix_file_before": record["matrix_file_before"],
            "matrix_file_after": matrix_after_file,
            "matrix_memory_before": record["matrix_memory_before"],
            "matrix_memory_after": matrix_after_memory,
            "index_file_before": record["index_file_before"],
            "index_file_after": index_after_file,
            "index_memory_before": record["index_memory_before"],
            "index_memory_after": index_after_memory,
            "unchanged": bool(
                record["matrix_file_before"] == matrix_after_file
                and record["matrix_memory_before"] == matrix_after_memory
                and record["index_file_before"] == index_after_file
                and record["index_memory_before"] == index_after_memory
            ),
        }
    return result


def _flat_immutable_artifacts(records: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    flattened: list[Mapping[str, Any]] = []
    for name, record in records.items():
        matrix_kind = "semantic_matrix" if name == "semantic" else "bpr_matrix"
        index_kind = "semantic_index" if name == "semantic" else "bpr_index"
        flattened.extend(
            (
                {
                    "name": f"{name}_matrix",
                    "kind": matrix_kind,
                    "file": record["matrix_file"],
                    "before": record["matrix_file_before"],
                    "after": record["matrix_file_after"],
                    "memory_before": record["matrix_memory_before"],
                    "memory_after": record["matrix_memory_after"],
                    "file_sha256_before": record["matrix_file_before"],
                    "file_sha256_after": record["matrix_file_after"],
                    "memory_sha256_before": record["matrix_memory_before"],
                    "memory_sha256_after": record["matrix_memory_after"],
                    "unchanged": bool(
                        record["matrix_file_before"] == record["matrix_file_after"]
                        and record["matrix_memory_before"] == record["matrix_memory_after"]
                    ),
                },
                {
                    "name": f"{name}_index",
                    "kind": index_kind,
                    "file": record["index_file"],
                    "before": record["index_file_before"],
                    "after": record["index_file_after"],
                    "memory_before": record["index_memory_before"],
                    "memory_after": record["index_memory_after"],
                    "file_sha256_before": record["index_file_before"],
                    "file_sha256_after": record["index_file_after"],
                    "memory_sha256_before": record["index_memory_before"],
                    "memory_sha256_after": record["index_memory_after"],
                    "unchanged": bool(
                        record["index_file_before"] == record["index_file_after"]
                        and record["index_memory_before"] == record["index_memory_after"]
                    ),
                },
            )
        )
    return flattened


def finalize_candidate(
    run_directory: Path,
    lock: RunnerLock,
    result: Mapping[str, Any],
    execution_sha256: str,
    source_hashes: Mapping[str, str],
    dataset_sha256: str,
    environment_path: Path,
    error_ledger: Path,
    raw_validation_path: Path,
    raw_test_path: Path | None,
    latency_path: Path | None,
    python_executable_sha256: str,
) -> Path:
    short = execution_sha256[:16]
    result_path = run_directory / f"result_{short}_seq001.json"
    core.publish_json_no_overwrite(result_path, result)
    if error_ledger.stat().st_size != 0:
        raise IntegrityError("Asynchronous ledger is nonempty")
    artifact_hashes = core.collect_artifact_hashes(run_directory)
    candidate: dict[str, Any] = {
        "schema": "facet-pref-runner-completion-candidate-v1",
        "created_utc": core.utc_now(),
        "pid": os.getpid(),
        "run_directory": str(run_directory),
        "termination_stage": result["termination_stage"],
        "test_opened": bool(result["test_opened"]),
        "execution_fingerprint_sha256": execution_sha256,
        "result_file": result_path.name,
        "result_sha256": artifact_hashes[result_path.name],
        "raw_validation_power_file": raw_validation_path.name,
        "raw_validation_power_sha256": artifact_hashes[raw_validation_path.name],
        "asynchronous_error_ledger": error_ledger.name,
        "asynchronous_error_ledger_sha256": artifact_hashes[error_ledger.name],
        "source_sha256": dict(source_hashes),
        "dataset_archive_sha256": dataset_sha256,
        "python_executable": sys.executable,
        "python_executable_sha256": python_executable_sha256,
        "environment_file": environment_path.name,
        "environment_sha256": artifact_hashes[environment_path.name],
        "artifact_sha256": artifact_hashes,
        "runner_lock": str(lock.path),
        "runner_lock_token": lock.token,
        "runner_lock_release_pending": True,
        "external_post_exit_verification_required": True,
    }
    if raw_test_path is not None:
        candidate["raw_test_arrays_file"] = raw_test_path.name
        candidate["raw_test_arrays_sha256"] = artifact_hashes[raw_test_path.name]
    if latency_path is not None:
        candidate["latency_file"] = latency_path.name
        candidate["latency_sha256"] = artifact_hashes[latency_path.name]
    marker = run_directory / f"RUNNER_COMPLETE_CANDIDATE_{short}.json"
    core.publish_json_no_overwrite(marker, candidate)
    print(f"RESULT_FILE={result_path}", flush=True)
    print(f"RUNNER_COMPLETION_MARKER={marker}", flush=True)
    return marker


def execute(args: argparse.Namespace) -> Path:
    config_path = args.config.resolve()
    protocol_path = args.protocol.resolve()
    output_directory = args.output_dir.resolve()
    if not config_path.is_file():
        raise FileNotFoundError(config_path)
    if not protocol_path.is_file():
        raise FileNotFoundError(protocol_path)
    config_bytes = config_path.read_bytes()
    config = json.loads(config_bytes.decode("utf-8"))
    validate_config(config)
    environment_mismatches = {
        key: os.environ.get(key)
        for key, expected in FIXED_EXECUTION_ENVIRONMENT.items()
        if os.environ.get(key) != expected
    }
    if environment_mismatches or not sys.dont_write_bytecode:
        raise IntegrityError(
            f"Outcome execution environment is not launcher-locked: {environment_mismatches}"
        )
    runner_path = Path(__file__).resolve()
    core_path = Path(core.__file__).resolve()
    project_root = runner_path.parents[1]
    locked_config_path = (project_root / "src" / "configs" / "facet_pref_poc_ml1m_v1.json").resolve()
    locked_protocol_path = (project_root / "experiments" / "facet-pref-protocol-v1.md").resolve()
    if config_path != locked_config_path or protocol_path != locked_protocol_path:
        raise IntegrityError("Outcome execution requires the exact project-locked config and protocol paths")
    if core.sha256_bytes(config_bytes) != LOCKED_CONFIG_SHA256:
        raise IntegrityError("Locked FACET-PREF config SHA-256 changed")
    if core.sha256_file(protocol_path) != LOCKED_PROTOCOL_SHA256:
        raise IntegrityError("Locked FACET-PREF protocol SHA-256 changed")
    question_path = project_root / "research-question-cycle4.md"
    survey_path = project_root / "literature" / "cycle4-survey-and-ideation.md"
    architecture_path = project_root / "architecture-facet-pref.md"
    for required in (question_path, survey_path, architecture_path):
        if not required.is_file():
            raise FileNotFoundError(required)
    source_hashes = {
        "runner": core.sha256_file(runner_path),
        "config": core.sha256_bytes(config_bytes),
        "protocol": core.sha256_file(protocol_path),
        "caper_dependency": core.sha256_file(core_path),
        "research_question": core.sha256_file(question_path),
        "cycle4_survey": core.sha256_file(survey_path),
        "architecture_facet_pref": core.sha256_file(architecture_path),
    }
    protocol_sha = core.sha256_bytes(
        core.canonical_json_bytes(
            {"protocol_name": config["protocol_name"], "source_sha256": source_hashes}
        )
    )
    short = protocol_sha[:16]
    lock = RunnerLock(output_directory.parent / "facet_pref_poc.lock", protocol_sha)
    lock.acquire()
    run_directory: Path | None = None
    try:
        if output_directory.exists():
            raise IntegrityError("--output-dir must not already exist")
        output_directory.mkdir(parents=True, exist_ok=False)
        run_directory = output_directory
        snapshots: dict[str, Path] = {}
        for label, source in (
            ("runner", runner_path),
            ("protocol", protocol_path),
            ("caper_dependency", core_path),
            ("research_question", question_path),
            ("cycle4_survey", survey_path),
            ("architecture_facet_pref", architecture_path),
        ):
            destination = run_directory / f"source_{label}_{core.sha256_file(source)[:16]}_seq001{source.suffix}"
            core.publish_bytes_no_overwrite(destination, source.read_bytes())
            snapshots[label] = destination
        effective_config = run_directory / f"effective_config_{source_hashes['config'][:16]}_seq001.json"
        core.publish_bytes_no_overwrite(effective_config, config_bytes)
        python_path = Path(sys.executable).resolve()
        python_sha = core.sha256_file(python_path)
        environment_path = run_directory / f"environment_{short}_seq001.json"
        try:
            import faiss
            faiss_version = getattr(faiss, "__version__", "unknown")
        except ImportError:
            faiss_version = "missing"
        core.publish_json_no_overwrite(
            environment_path,
            {
                "schema": "facet-pref-environment-v1",
                "created_utc": core.utc_now(),
                "python_executable": str(python_path),
                "python_executable_sha256": python_sha,
                "python_version": sys.version,
                "platform": platform.platform(),
                "numpy_version": np.__version__,
                "torch_version": torch.__version__,
                "torch_intraop_threads": torch.get_num_threads(),
                "torch_interop_threads": torch.get_num_interop_threads(),
                "faiss_version": faiss_version,
                "sentence_transformers_version": importlib.metadata.version("sentence-transformers"),
                "thread_environment": THREAD_ENVIRONMENT,
                "fixed_execution_environment": dict(FIXED_EXECUTION_ENVIRONMENT),
                "fixed_execution_environment_observed": {
                    key: os.environ.get(key) for key in FIXED_EXECUTION_ENVIRONMENT
                },
                "python_dont_write_bytecode": bool(sys.dont_write_bytecode),
                "source_snapshots": {
                    label: {"file": path.name, "sha256": core.sha256_file(path)}
                    for label, path in snapshots.items()
                },
            },
        )
        error_ledger = run_directory / f"async_errors_{short}_seq001.jsonl"
        event_log = run_directory / f"events_{short}_seq001.jsonl"
        for path in (error_ledger, event_log):
            with path.open("xb") as handle:
                handle.flush()
                os.fsync(handle.fileno())
        core.install_async_exception_hooks(error_ledger)

        def log_event(event: str, **values: Any) -> None:
            core.append_json_line(
                event_log,
                {"utc": core.utc_now(), "ns": time.time_ns(), "event": event, "pid": os.getpid(), **values},
            )

        log_event("run_started", protocol_sha256=protocol_sha, source_sha256=source_hashes)
        archive_path = run_directory / "ml-1m.sha-locked.zip"
        dataset_sha, acquisition_mode = acquire_locked_archive(
            archive_path,
            str(config["dataset"]["official_url"]),
            str(config["dataset"]["expected_archive_sha256"]),
            args.local_dataset_archive,
        )
        ratings_path, movies_path = core.extract_movielens(
            archive_path, run_directory / "sha_locked_ml1m_extracted"
        )
        extraction_hashes = {
            "ratings.dat": core.sha256_file(ratings_path),
            "movies.dat": core.sha256_file(movies_path),
        }
        movie_ids, metadata = core.load_movie_metadata(
            movies_path, str(config["embedding"]["metadata_template"])
        )
        item_to_index = {movie_id: index for index, movie_id in enumerate(movie_ids)}
        interactions = core.load_ratings(ratings_path, item_to_index)
        splits, split_diagnostics = derive_facet_cohort(interactions, config)
        a_splits, ar_splits, arv_splits = sealed_stage_views(splits)
        temporal = temporal_block_arrays(splits)
        cohort_path = run_directory / f"cohort_lock_{short}_seq001.json"
        core.publish_json_no_overwrite(
            cohort_path,
            {
                "schema": "facet-pref-prospective-cohort-v1",
                "protocol_sha256": protocol_sha,
                "diagnostics": split_diagnostics,
                "eligibility_disclosed_only_membership_and_offsets": True,
                "V_or_T_identity_rating_pair_opened": False,
            },
        )
        log_event("archive_extraction_and_cohort_locked", dataset_sha256=dataset_sha)

        semantic_vectors = core.encode_item_metadata(metadata, config["embedding"])
        if semantic_vectors.shape[1] != int(config["embedding"]["dimension"]):
            raise IntegrityError("SentenceTransformer embedding dimension changed")
        semantic_matrix_path = run_directory / f"semantic_matrix_{short}_seq001.npy"
        semantic_index_path = run_directory / f"semantic_index_{short}_seq001.faiss"
        core.save_numpy_no_overwrite(semantic_matrix_path, semantic_vectors)
        semantic_index = core.build_faiss_index(semantic_vectors, config["retrieval"])
        core.publish_bytes_no_overwrite(semantic_index_path, core.serialize_faiss(semantic_index))
        matrix_records: list[dict[str, Any]] = [
            {
                "name": "semantic",
                "matrix_path": semantic_matrix_path,
                "matrix": semantic_vectors,
                "index_path": semantic_index_path,
                "index": semantic_index,
                "matrix_file_before": core.sha256_file(semantic_matrix_path),
                "matrix_memory_before": core.sha256_bytes(semantic_vectors.tobytes(order="C")),
                "index_file_before": core.sha256_file(semantic_index_path),
                "index_memory_before": core.sha256_bytes(core.serialize_faiss(semantic_index)),
            }
        ]
        bprs: dict[str, BPRArtifacts] = {}
        bpr_indexes: dict[str, Any] = {}
        bpr_checkpoint_paths: dict[str, str] = {}
        for variant in ("implicit", "rating_aware"):
            bpr, state = core.train_bpr(
                a_splits,
                len(movie_ids),
                variant,
                config["bpr"],
                int(config["determinism_seed"]),
            )
            index = core.build_faiss_index(bpr.item_vectors, config["retrieval"])
            bprs[variant] = bpr
            bpr_indexes[variant] = index
            matrix_path = run_directory / f"bpr_{variant}_matrix_{short}_seq001.npy"
            index_path = run_directory / f"bpr_{variant}_index_{short}_seq001.faiss"
            checkpoint_path = run_directory / f"bpr_{variant}_checkpoint_{short}_seq001.pt"
            core.save_numpy_no_overwrite(matrix_path, bpr.item_vectors)
            core.publish_bytes_no_overwrite(index_path, core.serialize_faiss(index))
            core.save_torch_no_overwrite(
                checkpoint_path,
                {
                    "protocol_sha256": protocol_sha,
                    "variant": variant,
                    "seed": int(config["determinism_seed"]),
                    "state_dict": state,
                    "diagnostics": dict(bpr.training_diagnostics),
                },
            )
            bpr_checkpoint_paths[variant] = checkpoint_path.name
            matrix_records.append(
                {
                    "name": f"bpr_{variant}",
                    "matrix_path": matrix_path,
                    "matrix": bpr.item_vectors,
                    "index_path": index_path,
                    "index": index,
                    "matrix_file_before": core.sha256_file(matrix_path),
                    "matrix_memory_before": core.sha256_bytes(bpr.item_vectors.tobytes(order="C")),
                    "index_file_before": core.sha256_file(index_path),
                    "index_memory_before": core.sha256_bytes(core.serialize_faiss(index)),
                }
            )
        log_event("A_only_representations_and_indexes_locked")

        stage_times: dict[str, int] = {}
        r_full, r_single, r_descriptor_rows = build_descriptor_manifest(
            a_splits, semantic_vectors, movie_ids, config, "R"
        )
        r_descriptor_path = run_directory / f"R_target_blind_descriptors_{short}_seq001.json"
        core.publish_json_no_overwrite(
            r_descriptor_path,
            {
                "schema": "facet-pref-R-descriptors-v1",
                "protocol_sha256": protocol_sha,
                "created_before_R_target_join": True,
                "rows": r_descriptor_rows,
            },
        )
        stage_times["R_manifest_published_ns"] = time.time_ns()
        log_event("R_descriptors_published", file=r_descriptor_path.name)
        stage_times["R_target_joined_ns"] = time.time_ns()
        corpus, pair_rows = build_pair_corpus(
            ar_splits, r_full, semantic_vectors, movie_ids, config
        )
        if stage_times["R_target_joined_ns"] <= stage_times["R_manifest_published_ns"]:
            raise IntegrityError("R target joined before descriptor publication")
        pair_pool_path = run_directory / f"R_natural_pair_pool_{short}_seq001.json"
        core.publish_json_no_overwrite(
            pair_pool_path,
            {
                "schema": "facet-pref-R-pair-pool-v1",
                "protocol_sha256": protocol_sha,
                "source_descriptor_sha256": core.sha256_file(r_descriptor_path),
                "diagnostics": dict(corpus.diagnostics),
                "pairs": pair_rows,
            },
        )
        single_corpus = single_query_corpus(corpus, r_single)
        log_event("R_natural_pair_corpus_joined", selected_pairs=len(corpus.user_ids))

        adapters_by_seed: dict[int, dict[str, QueryAdapter]] = {}
        adapter_diagnostics: dict[str, Any] = {}
        adapter_checkpoint_paths: dict[str, str] = {}
        adapter_memory_before: dict[str, str] = {}
        for seed in map(int, config["optimization_seeds"]):
            initial_state = _adapter_initial_state(config, seed)
            initial_path = run_directory / f"adapter_initial_seed{seed}_{short}_seq001.pt"
            core.save_torch_no_overwrite(
                initial_path,
                {
                    "protocol_sha256": protocol_sha,
                    "seed": seed,
                    "state_dict": initial_state,
                    "shared_by_all_aligned_controls": True,
                },
            )
            adapter_checkpoint_paths[f"initial_seed{seed}"] = initial_path.name
            adapters_by_seed[seed] = {}
            specifications = (
                ("single_query_aligned", single_corpus, float(config["alignment"]["margin"]), "user_facet_macro", False),
                ("multi_facet_zero_margin", corpus, float(config["controls"]["zero_margin_value"]), "user_facet_macro", False),
                ("multi_facet_shuffled_direction", corpus, float(config["alignment"]["margin"]), "user_facet_macro", True),
                ("multi_facet_pair_micro", corpus, float(config["alignment"]["margin"]), "pair_micro", False),
                ("facet_pref", corpus, float(config["alignment"]["margin"]), "user_facet_macro", False),
            )
            for method_name, method_corpus, margin, weighting, shuffle in specifications:
                adapter, diagnostics, state = train_adapter(
                    method_corpus,
                    config,
                    seed,
                    margin,
                    weighting,
                    shuffle,
                    initial_state,
                )
                adapters_by_seed[seed][method_name] = adapter
                key = f"{method_name}_seed{seed}"
                checkpoint_path = run_directory / f"adapter_{method_name}_seed{seed}_{short}_seq001.pt"
                core.save_torch_no_overwrite(
                    checkpoint_path,
                    {
                        "protocol_sha256": protocol_sha,
                        "seed": seed,
                        "method": method_name,
                        "state_dict": state,
                        "diagnostics": diagnostics,
                    },
                )
                adapter_diagnostics[key] = diagnostics
                adapter_checkpoint_paths[key] = checkpoint_path.name
                adapter_memory_before[key] = adapter_memory_sha256(adapter)
        log_event("all_R_only_aligned_models_trained")

        v_full, v_single, v_descriptor_rows = build_descriptor_manifest(
            ar_splits, semantic_vectors, movie_ids, config, "V"
        )
        v_descriptor_path = run_directory / f"V_target_blind_descriptors_{short}_seq001.json"
        core.publish_json_no_overwrite(
            v_descriptor_path,
            {
                "schema": "facet-pref-V-descriptors-v1",
                "protocol_sha256": protocol_sha,
                "created_before_V_label_join": True,
                "rows": v_descriptor_rows,
            },
        )
        validation_manifests: dict[int, dict[str, RawManifest]] = {}
        validation_manifest_paths: dict[str, Path] = {}
        validation_manifest_hashes: dict[str, str] = {}
        for seed in map(int, config["optimization_seeds"]):
            validation_manifests[seed] = {}
            for variant in ("implicit", "rating_aware"):
                manifest = build_raw_manifest(
                    ar_splits,
                    "V",
                    v_full,
                    v_single,
                    adapters_by_seed[seed],
                    bprs[variant],
                    bpr_indexes[variant],
                    semantic_vectors,
                    semantic_index,
                    movie_ids,
                    config,
                    None,
                )
                path = run_directory / f"V_manifest_{variant}_seed{seed}_{short}_seq001.npz"
                manifest_hash = publish_manifest(path, manifest, protocol_sha, "V", seed, variant, False)
                validation_manifests[seed][variant] = manifest
                manifest_key = f"{variant}_seed{seed}"
                validation_manifest_paths[manifest_key] = path
                validation_manifest_hashes[manifest_key] = manifest_hash
        stage_times["V_manifest_published_ns"] = time.time_ns()
        log_event("all_V_alpha_grid_manifests_published")
        stage_times["V_relevance_joined_ns"] = time.time_ns()
        selected_variant, selected_alpha, selection = select_bpr_and_alpha(
            validation_manifests, splits, config
        )
        if stage_times["V_relevance_joined_ns"] <= stage_times["V_manifest_published_ns"]:
            raise IntegrityError("V relevance joined before all manifests were published")
        selection_path = run_directory / f"V_relevance_selection_lock_{short}_seq001.json"
        core.publish_json_no_overwrite(
            selection_path,
            {
                "schema": "facet-pref-V-selection-v1",
                "protocol_sha256": protocol_sha,
                "manifest_sha256": {
                    key: core.sha256_file(path) for key, path in validation_manifest_paths.items()
                },
                **selection,
            },
        )
        selected_bpr = bprs[selected_variant]
        selected_bpr_index = bpr_indexes[selected_variant]
        fused_validation = {
            seed: apply_fusion_to_manifest(
                validation_manifests[seed][selected_variant], selected_alpha, movie_ids
            )
            for seed in map(int, config["optimization_seeds"])
        }
        freeze_artifacts: dict[str, str] = {
            selection_path.name: core.sha256_file(selection_path),
            semantic_matrix_path.name: core.sha256_file(semantic_matrix_path),
            semantic_index_path.name: core.sha256_file(semantic_index_path),
        }
        for record in matrix_records[1:]:
            freeze_artifacts[Path(record["matrix_path"]).name] = core.sha256_file(record["matrix_path"])
            freeze_artifacts[Path(record["index_path"]).name] = core.sha256_file(record["index_path"])
        for path_name in adapter_checkpoint_paths.values():
            checkpoint_path = run_directory / path_name
            freeze_artifacts[path_name] = core.sha256_file(checkpoint_path)
        for path in validation_manifest_paths.values():
            freeze_artifacts[path.name] = core.sha256_file(path)
        freeze_path = run_directory / f"pre_power_freeze_lock_{short}_seq001.json"
        core.publish_json_no_overwrite(
            freeze_path,
            {
                "schema": "facet-pref-pre-power-freeze-v1",
                "protocol_sha256": protocol_sha,
                "selected_bpr_variant": selected_variant,
                "selected_alpha": selected_alpha,
                "artifact_sha256": freeze_artifacts,
                "V_preference_opened": False,
                "choices_may_change_after_this_lock": False,
            },
        )
        stage_times["choices_frozen_ns"] = time.time_ns()
        stage_times["V_preference_joined_ns"] = time.time_ns()
        v_outcomes = build_outcome_arrays(splits, "V", movie_ids, config)
        power_audit, power_differences, power_lower_bounds, validation_top10 = run_validation_power_audit(
            fused_validation, v_outcomes, config
        )
        if not (
            stage_times["V_relevance_joined_ns"]
            < stage_times["choices_frozen_ns"]
            < stage_times["V_preference_joined_ns"]
        ):
            raise IntegrityError("V preference opened before the complete choice freeze")
        raw_validation_path = run_directory / f"raw_validation_power_{short}_seq001.npz"
        publish_raw_validation_power(
            raw_validation_path,
            v_outcomes,
            validation_top10,
            power_differences,
            power_lower_bounds,
            power_audit,
            corpus,
            split_diagnostics,
            temporal,
            movie_ids,
            config,
            protocol_sha,
            stage_times,
            selection,
            validation_manifest_paths,
            splits,
            pair_pool_path,
        )
        log_event("V_preference_power_audit_complete", passed=bool(power_audit["passed"]))

        matrix_index_hashes = _matrix_index_after_records(matrix_records)
        adapter_model_hashes = {
            key: {
                "before": before,
                "after": adapter_memory_sha256(
                    adapters_by_seed[int(key.rsplit("seed", 1)[1])][key.rsplit("_seed", 1)[0]]
                ),
            }
            for key, before in adapter_memory_before.items()
        }
        for record in adapter_model_hashes.values():
            record["unchanged"] = record["before"] == record["after"]
        manifests_stable = all(
            core.sha256_file(validation_manifest_paths[key]) == expected
            for key, expected in validation_manifest_hashes.items()
        )
        base_integrity = {
            "archive_sha256": dataset_sha,
            "extraction_sha256": extraction_hashes,
            "extraction_files": {
                "ratings.dat": {"file": ratings_path.relative_to(run_directory).as_posix(), "sha256": extraction_hashes["ratings.dat"]},
                "movies.dat": {"file": movies_path.relative_to(run_directory).as_posix(), "sha256": extraction_hashes["movies.dat"]},
            },
            "cohort": {
                "caper_user_ids_sha256": split_diagnostics["caper_user_ids_sha256"],
                "ravel_user_ids_sha256": split_diagnostics["ravel_user_ids_sha256"],
                "facet_user_ids_sha256": split_diagnostics["facet_user_ids_sha256"],
                "pairwise_disjoint": split_diagnostics["cohorts_pairwise_disjoint"],
                "strict_temporal_boundaries": split_diagnostics["strict_temporal_boundaries"],
                "timestamp_groups_indivisible": split_diagnostics["timestamp_groups_indivisible"],
            },
            "matrix_index_hashes": matrix_index_hashes,
            "immutable_artifacts": _flat_immutable_artifacts(matrix_index_hashes),
            "all_matrices_and_indexes_unchanged": all(
                record["unchanged"] for record in matrix_index_hashes.values()
            ),
            "adapter_model_hashes": adapter_model_hashes,
            "all_adapter_models_unchanged": all(
                record["unchanged"] for record in adapter_model_hashes.values()
            ),
            "target_blind_order": {
                "R_manifest_before_join": stage_times["R_manifest_published_ns"] < stage_times["R_target_joined_ns"],
                "V_manifest_before_relevance": stage_times["V_manifest_published_ns"] < stage_times["V_relevance_joined_ns"],
                "V_relevance_before_freeze": stage_times["V_relevance_joined_ns"] < stage_times["choices_frozen_ns"],
                "freeze_before_V_preference": stage_times["choices_frozen_ns"] < stage_times["V_preference_joined_ns"],
            },
            "source_sha256": source_hashes,
            "source_snapshots_stable": bool(
                core.sha256_file(runner_path) == source_hashes["runner"]
                and core.sha256_file(protocol_path) == source_hashes["protocol"]
                and core.sha256_file(core_path) == source_hashes["caper_dependency"]
                and core.sha256_file(question_path) == source_hashes["research_question"]
                and core.sha256_file(survey_path) == source_hashes["cycle4_survey"]
                and core.sha256_file(architecture_path) == source_hashes["architecture_facet_pref"]
                and core.sha256_file(config_path) == source_hashes["config"]
                and core.sha256_file(snapshots["runner"]) == source_hashes["runner"]
                and core.sha256_file(snapshots["protocol"]) == source_hashes["protocol"]
                and core.sha256_file(snapshots["caper_dependency"]) == source_hashes["caper_dependency"]
                and core.sha256_file(snapshots["research_question"]) == source_hashes["research_question"]
                and core.sha256_file(snapshots["cycle4_survey"]) == source_hashes["cycle4_survey"]
                and core.sha256_file(snapshots["architecture_facet_pref"]) == source_hashes["architecture_facet_pref"]
                and core.sha256_file(effective_config) == source_hashes["config"]
            ),
            "archive_stable": core.sha256_file(archive_path) == dataset_sha,
            "extraction_stable": bool(
                core.sha256_file(ratings_path) == extraction_hashes["ratings.dat"]
                and core.sha256_file(movies_path) == extraction_hashes["movies.dat"]
            ),
            "python_executable": str(python_path),
            "python_executable_sha256": python_sha,
            "environment_sha256": core.sha256_file(environment_path),
            "validation_manifest_sha256": {
                key: core.sha256_file(path) for key, path in validation_manifest_paths.items()
            },
            "pre_power_freeze_file": freeze_path.name,
            "pre_power_freeze_sha256": core.sha256_file(freeze_path),
            "frozen_artifacts_stable": all(
                core.sha256_file(run_directory / name) == expected
                for name, expected in freeze_artifacts.items()
            ),
            "manifests_stable": manifests_stable,
            "asynchronous_error_ledger_empty": error_ledger.stat().st_size == 0,
        }
        execution_sha = core.sha256_bytes(
            core.canonical_json_bytes(
                {
                    "protocol_sha256": protocol_sha,
                    "dataset_sha256": dataset_sha,
                    "facet_user_ids_sha256": split_diagnostics["facet_user_ids_sha256"],
                    "selected_bpr_variant": selected_variant,
                    "selected_alpha": selected_alpha,
                    "optimization_seeds": config["optimization_seeds"],
                }
            )
        )
        execution_short = execution_sha[:16]

        if not power_audit["passed"]:
            negative_gate = {
                "G1": "not_evaluated",
                "G2": "not_evaluated",
                "G3": "not_evaluated",
                "G4": "not_evaluated",
                "G5": "not_evaluated",
                "G6": False,
                "G7": "not_evaluated",
                "G8": "not_evaluated",
                "G9": bool(
                    base_integrity["all_matrices_and_indexes_unchanged"]
                    and base_integrity["all_adapter_models_unchanged"]
                    and base_integrity["asynchronous_error_ledger_empty"]
                    and base_integrity["source_snapshots_stable"]
                    and base_integrity["archive_stable"]
                    and base_integrity["extraction_stable"]
                    and base_integrity["cohort"]["pairwise_disjoint"]
                    and base_integrity["cohort"]["strict_temporal_boundaries"]
                    and all(base_integrity["target_blind_order"].values())
                ),
            }
            result = {
                "schema": "facet-pref-poc-result-v1",
                "status": "SCIENTIFIC_NEGATIVE_PRE_T_KILL",
                "termination_stage": "pre_T_power_audit",
                "test_opened": False,
                "PROMISING": False,
                "protocol_sha256": protocol_sha,
                "execution_fingerprint_sha256": execution_sha,
                "created_utc": core.utc_now(),
                "selection_locks": selection,
                "power_audit": power_audit,
                "promise_gate": {"gates": negative_gate, "PROMISING": False},
                "alignment_diagnostics": dict(corpus.diagnostics),
                "adapter_diagnostics": adapter_diagnostics,
                "integrity": base_integrity,
                "provenance": {
                    "acquisition_mode": acquisition_mode,
                    "bpr_checkpoints": bpr_checkpoint_paths,
                    "adapter_checkpoints": adapter_checkpoint_paths,
                    "T_artifacts_created": False,
                },
            }
            return finalize_candidate(
                run_directory,
                lock,
                result,
                execution_sha,
                source_hashes,
                dataset_sha,
                environment_path,
                error_ledger,
                raw_validation_path,
                None,
                None,
                python_sha,
            )

        # V power passed.  Only now may target-blind T manifests be built.
        t_full, t_single, t_descriptor_rows = build_descriptor_manifest(
            arv_splits, semantic_vectors, movie_ids, config, "T"
        )
        t_descriptor_path = run_directory / f"T_target_blind_descriptors_{execution_short}_seq001.json"
        core.publish_json_no_overwrite(
            t_descriptor_path,
            {
                "schema": "facet-pref-T-descriptors-v1",
                "protocol_sha256": protocol_sha,
                "created_before_T_target_join": True,
                "rows": t_descriptor_rows,
            },
        )
        test_manifests: dict[int, RawManifest] = {}
        test_manifest_paths: dict[str, Path] = {}
        test_manifest_hashes: dict[str, str] = {}
        for seed in map(int, config["optimization_seeds"]):
            manifest = build_raw_manifest(
                arv_splits,
                "T",
                t_full,
                t_single,
                adapters_by_seed[seed],
                selected_bpr,
                selected_bpr_index,
                semantic_vectors,
                semantic_index,
                movie_ids,
                config,
                selected_alpha,
            )
            path = run_directory / f"T_manifest_seed{seed}_{execution_short}_seq001.npz"
            manifest_hash = publish_manifest(path, manifest, protocol_sha, "T", seed, selected_variant, False)
            test_manifests[seed] = manifest
            test_manifest_paths[str(seed)] = path
            test_manifest_hashes[str(seed)] = manifest_hash
        stage_times["T_manifest_published_ns"] = time.time_ns()
        log_event("all_T_manifests_published_before_T_open")
        stage_times["T_target_joined_ns"] = time.time_ns()
        t_outcomes = build_outcome_arrays(splits, "T", movie_ids, config)
        if stage_times["T_target_joined_ns"] <= stage_times["T_manifest_published_ns"]:
            raise IntegrityError("T opened before complete manifest publication")
        if t_outcomes.total_pairs < int(config["evaluation"]["minimum_fixed_test_pairs"]):
            raise IntegrityError("T fixed-pair floor failed")
        if t_outcomes.pair_bearing_users < int(config["evaluation"]["minimum_test_pair_bearing_users"]):
            raise IntegrityError("T pair-bearing-user floor failed")
        log_event("T_opened_exactly_once", fixed_pairs=t_outcomes.total_pairs)
        metric_rows: list[np.ndarray] = []
        pair_diagnostics: list[Mapping[str, int]] = []
        for seed in map(int, config["optimization_seeds"]):
            seed_metrics, diagnostics = evaluate_manifest(test_manifests[seed], t_outcomes, config)
            metric_rows.append(seed_metrics)
            pair_diagnostics.append(diagnostics)
        metrics = np.stack(metric_rows)
        stacked = stack_test_manifests(test_manifests, config)
        raw_test_path = run_directory / f"raw_test_arrays_{execution_short}_seq001.npz"
        publish_raw_test_arrays(
            raw_test_path,
            stacked,
            metrics,
            t_outcomes,
            pair_diagnostics,
            split_diagnostics,
            temporal,
            movie_ids,
            config,
            protocol_sha,
            stage_times,
            selected_alpha,
            selected_variant,
            test_manifest_paths,
        )
        durations, latency_summary = benchmark_latency(
            arv_splits,
            adapters_by_seed,
            selected_bpr,
            selected_bpr_index,
            semantic_vectors,
            semantic_index,
            movie_ids,
            selected_alpha,
            config,
        )
        latency_path = run_directory / f"latency_{execution_short}_seq001.npz"
        publish_latency_arrays(latency_path, durations, latency_summary, protocol_sha, config)
        matrix_index_hashes = _matrix_index_after_records(matrix_records)
        adapter_model_hashes = {
            key: {
                "before": before,
                "after": adapter_memory_sha256(
                    adapters_by_seed[int(key.rsplit("seed", 1)[1])][key.rsplit("_seed", 1)[0]]
                ),
            }
            for key, before in adapter_memory_before.items()
        }
        for record in adapter_model_hashes.values():
            record["unchanged"] = record["before"] == record["after"]
        test_manifests_stable = all(
            core.sha256_file(test_manifest_paths[seed]) == expected
            for seed, expected in test_manifest_hashes.items()
        )
        integrity = {
            **base_integrity,
            "matrix_index_hashes": matrix_index_hashes,
            "immutable_artifacts": _flat_immutable_artifacts(matrix_index_hashes),
            "all_matrices_and_indexes_unchanged": all(
                record["unchanged"] for record in matrix_index_hashes.values()
            ),
            "adapter_model_hashes": adapter_model_hashes,
            "all_adapter_models_unchanged": all(
                record["unchanged"] for record in adapter_model_hashes.values()
            ),
            "target_blind_order": {
                **base_integrity["target_blind_order"],
                "T_manifest_before_join": stage_times["T_manifest_published_ns"] < stage_times["T_target_joined_ns"],
            },
            "test_manifest_sha256": {
                seed: core.sha256_file(path) for seed, path in test_manifest_paths.items()
            },
            "test_manifests_stable": test_manifests_stable,
            "frozen_artifacts_stable": all(
                core.sha256_file(run_directory / name) == expected
                for name, expected in freeze_artifacts.items()
            ),
        }
        internal_integrity = bool(
            integrity["all_matrices_and_indexes_unchanged"]
            and integrity["cohort"]["pairwise_disjoint"]
            and integrity["cohort"]["strict_temporal_boundaries"]
            and integrity["cohort"]["timestamp_groups_indivisible"]
            and all(integrity["target_blind_order"].values())
            and integrity["manifests_stable"]
            and integrity["test_manifests_stable"]
            and integrity["asynchronous_error_ledger_empty"]
            and integrity["all_adapter_models_unchanged"]
            and integrity["source_snapshots_stable"]
            and integrity["archive_stable"]
            and integrity["extraction_stable"]
            and integrity["frozen_artifacts_stable"]
            and core.sha256_file(python_path) == python_sha
        )
        promise_gate = evaluate_gates_from_arrays(
            metrics,
            stacked["candidates"],
            t_outcomes,
            corpus.diagnostics,
            power_audit,
            pair_diagnostics,
            latency_summary,
            internal_integrity,
            config,
            stacked["retrieval_diagnostics"],
        )
        result = {
            "schema": "facet-pref-poc-result-v1",
            "status": "COMPLETE_RUNNER_RESULT",
            "termination_stage": "post_T_all_gates",
            "test_opened": True,
            "PROMISING": False,
            "runner_candidate_promising": promise_gate["runner_candidate_promising"],
            "protocol_sha256": protocol_sha,
            "execution_fingerprint_sha256": execution_sha,
            "created_utc": core.utc_now(),
            "selection_locks": selection,
            "power_audit": power_audit,
            "promise_gate": promise_gate,
            "alignment_diagnostics": dict(corpus.diagnostics),
            "adapter_diagnostics": adapter_diagnostics,
            "integrity": integrity,
            "provenance": {
                "acquisition_mode": acquisition_mode,
                "bpr_checkpoints": bpr_checkpoint_paths,
                "adapter_checkpoints": adapter_checkpoint_paths,
                "validation_manifests": {key: path.name for key, path in validation_manifest_paths.items()},
                "test_manifests": {seed: path.name for seed, path in test_manifest_paths.items()},
                "raw_validation_power": raw_validation_path.name,
                "raw_test_arrays": raw_test_path.name,
                "latency": latency_path.name,
                "T_artifacts_created": True,
                "T_open_count": 1,
            },
            "known_limitations": [
                "MovieLens ratings are exposure-conditioned and missing-not-at-random.",
                "PairSupport and sPCE are offline observed-rating estimands, not causal utility.",
                "Exact-index MovieLens latency does not establish million-item production latency.",
                "The method claims novelty only at the registered systems intersection.",
            ],
        }
        return finalize_candidate(
            run_directory,
            lock,
            result,
            execution_sha,
            source_hashes,
            dataset_sha,
            environment_path,
            error_ledger,
            raw_validation_path,
            raw_test_path,
            latency_path,
            python_sha,
        )
    except BaseException as exc:
        if run_directory is not None and run_directory.exists():
            error_path = run_directory / (
                f"synchronous_error_{short}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}_{uuid.uuid4().hex}.json"
            )
            try:
                core.publish_json_no_overwrite(
                    error_path,
                    {
                        "schema": "facet-pref-synchronous-error-v1",
                        "utc": core.utc_now(),
                        "pid": os.getpid(),
                        "exception_type": type(exc).__name__,
                        "exception": str(exc),
                        "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
                    },
                )
            except Exception:
                pass
        raise
    finally:
        lock.release()


def synthetic_self_test(config: Mapping[str, Any]) -> Mapping[str, Any]:
    """Outcome-free deterministic unit checks; never loads MovieLens labels."""
    validate_config(config)
    if not set(CONTROL_METHODS).issubset(METHODS):
        raise AssertionError("A registered control is absent from METHODS")
    rng = np.random.default_rng(73)
    vectors = rng.normal(size=(900, int(config["embedding"]["dimension"]))).astype(np.float32)
    vectors = core.normalize_rows(vectors)
    movie_ids = list(range(10_000, 10_900))
    history = (
        Interaction(7, 0, 5, 1, 0),
        Interaction(7, 1, 4, 2, 1),
        Interaction(7, 2, 5, 3, 2),
        Interaction(7, 3, 1, 4, 3),
        Interaction(7, 4, 3, 5, 4),
    )
    first = build_facet_descriptor(7, history, vectors, movie_ids, config, False)
    second = build_facet_descriptor(7, history, vectors, movie_ids, config, False)
    if first.facet_members != second.facet_members or first.raw_facets.tobytes() != second.raw_facets.tobytes():
        raise AssertionError("Facet construction is not deterministic")
    swap_vectors = core.normalize_rows(
        np.asarray([[1.0, 0.0], [-1.0, 0.0], [-0.9, 0.1]], dtype=np.float32)
    )
    swap_clusters = _spherical_two_means(
        (0, 1, 2), swap_vectors, (100, 200, 50), 8
    )
    if swap_clusters != ((2, 1), (0,)):
        raise AssertionError(
            f"Per-iteration minimum-ID canonicalization failed: {swap_clusters}"
        )
    seed_test_vectors = core.normalize_rows(
        rng.normal(size=(12, 7)).astype(np.float32)
    )
    seed_test_ids = tuple(range(500, 488, -1))
    vectorized_pair = _least_similar_seed_pair(
        tuple(range(12)), seed_test_vectors, seed_test_ids
    )
    reference_candidates = []
    for left in range(12):
        for right in range(left + 1, 12):
            low_item, high_item = sorted(
                (left, right), key=lambda item: seed_test_ids[item]
            )
            reference_candidates.append(
                (
                    float(np.dot(seed_test_vectors[left], seed_test_vectors[right])),
                    seed_test_ids[low_item],
                    seed_test_ids[high_item],
                    low_item,
                    high_item,
                )
            )
    reference = min(reference_candidates)
    if vectorized_pair != (reference[3], reference[4]):
        raise AssertionError("Vectorized least-similar seed differs from reference loop")
    tie_vectors = np.eye(4, dtype=np.float32)
    tie_ids = (40, 10, 30, 20)
    if _least_similar_seed_pair((0, 1, 2, 3), tie_vectors, tie_ids) != (1, 3):
        raise AssertionError("Least-similar exact tie did not use lexicographic movie IDs")
    core.deterministic_setup(99)
    adapter = QueryAdapter(
        int(config["adapter"]["input_dimension"]),
        int(config["adapter"]["output_dimension"]),
        int(config["adapter"]["hidden_dimension"]),
    )
    aligned = apply_adapter(first, adapter, float(config["adapter"]["query_displacement_bound"]))
    if not np.allclose(aligned, first.raw_facets, rtol=0.0, atol=2e-7):
        raise AssertionError("Zero-output adapter does not preserve raw queries")
    clipped = _safe_quantile_normalize(np.asarray([-100.0, 0.0, 1.0, 100.0], dtype=np.float32))
    if float(np.min(clipped)) < 0.0 or float(np.max(clipped)) > 1.0:
        raise AssertionError("Quantile map is not clipped")
    semantic_index = core.build_faiss_index(vectors, config["retrieval"])
    semantic, quotas, retrieval_diagnostics, semantic_owners = search_semantic_novel(
        semantic_index,
        first.raw_facets,
        frozenset(range(5)),
        tuple(range(5, 205)),
        config,
    )
    if len(semantic) != 200 or len(set(semantic)) != 200 or set(semantic) & set(range(205)):
        raise AssertionError("Exact BPR-novel semantic retrieval failed")
    if len(first.raw_facets) == 2 and sum(quotas) != 200:
        raise AssertionError("Facet quota/backfill accounting failed")
    if retrieval_diagnostics[3] != 0:
        raise AssertionError("Lower-canonical duplicate ownership failed")
    if len(semantic_owners) != 200 or any(owner not in {0, 1} for owner in semantic_owners):
        raise AssertionError("Per-item semantic ownership was not persisted")
    tiny_config = json.loads(json.dumps(config))
    tiny_config["alignment"]["epochs"] = 1
    tiny_config["alignment"]["user_group_size"] = 2
    pair_count = 4
    facet_inputs = np.zeros((pair_count, 2, 1154), dtype=np.float32)
    facet_inputs[:, :, :384] = np.stack((first.raw_facets[0], first.raw_facets[-1]))
    facet_mask = np.ones((pair_count, 2), dtype=np.bool_)
    tiny_corpus = PairCorpus(
        user_ids=np.asarray([1, 1, 2, 2], dtype=np.int64),
        chosen_items=np.asarray([10, 11, 12, 13], dtype=np.int64),
        rejected_items=np.asarray([20, 21, 22, 23], dtype=np.int64),
        facet_inputs=facet_inputs,
        facet_mask=facet_mask,
        chosen_vectors=vectors[np.asarray([10, 11, 12, 13])],
        rejected_vectors=vectors[np.asarray([20, 21, 22, 23])],
        assigned_facets=np.asarray([0, 1, 0, 1], dtype=np.int64),
        macro_weights=np.ones(pair_count, dtype=np.float32),
        pair_keys=((1, 10, 20), (1, 11, 21), (2, 12, 22), (2, 13, 23)),
        diagnostics={},
    )
    trained, _diagnostics, _state = train_adapter(
        tiny_corpus,
        tiny_config,
        101,
        0.2,
        "user_facet_macro",
        False,
        _adapter_initial_state(tiny_config, 101),
    )
    if not all(torch.isfinite(value).all() for value in trained.state_dict().values()):
        raise AssertionError("Synthetic adapter training produced nonfinite state")
    synthetic_candidates = np.full((3, len(METHODS), 1, 400), -1, dtype=np.int32)
    synthetic_candidates[:, 0, 0, :200] = np.arange(200, dtype=np.int32)
    for method_row in range(1, len(METHODS)):
        synthetic_candidates[:, method_row, 0] = np.arange(400, dtype=np.int32)
    synthetic_diagnostics = np.zeros(
        (3, len(METHODS), 1, len(RETRIEVAL_DIAGNOSTICS)), dtype=np.int16
    )
    invariant = candidate_invariants(
        synthetic_candidates,
        np.full((1, 1), -1, dtype=np.int32),
        np.asarray([0], dtype=np.int16),
        synthetic_diagnostics,
    )
    if not invariant["passed"]:
        raise AssertionError(f"Synthetic candidate replay failed: {invariant}")
    return {
        "config_valid": True,
        "registered_control_names_exact": True,
        "deterministic_facets": True,
        "per_iteration_facet_canonicalization": True,
        "vectorized_seed_pair_matches_reference": True,
        "zero_output_adapter_identity": True,
        "quantile_clipped_to_unit_interval": True,
        "exact_200_BPR_novel_semantic_candidates": True,
        "lower_canonical_cross_facet_ownership": True,
        "per_item_semantic_ownership": True,
        "adapter_training_path_finite": True,
        "raw_candidate_invariant_replay": True,
        "target_outcomes_accessed": False,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Run the preregistered FACET-PREF MovieLens-1M proof of concept."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=project_root / "src" / "configs" / "facet_pref_poc_ml1m_v1.json",
        help="Locked JSON configuration.",
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=project_root / "experiments" / "facet-pref-protocol-v1.md",
        help="Locked human-readable protocol.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Exact unique nonexisting append-only run directory.",
    )
    parser.add_argument(
        "--local-dataset-archive",
        type=Path,
        default=None,
        help="Optional local ML-1M ZIP; its SHA-256 must match the locked archive.",
    )
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate the locked config without accessing data or outcomes.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run synthetic outcome-free unit checks and exit.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.validate_config or args.self_test:
        config = json.loads(args.config.resolve().read_text(encoding="utf-8"))
        validate_config(config)
        if args.self_test:
            print(json.dumps(synthetic_self_test(config), sort_keys=True), flush=True)
        else:
            print("CONFIG_VALID=true", flush=True)
        return 0
    if args.output_dir is None:
        raise ValueError("--output-dir is required for an outcome-capable run")
    completion = execute(args)
    if not completion.is_file():
        raise IntegrityError("FACET-PREF runner returned without a completion candidate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
