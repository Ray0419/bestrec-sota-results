#!/usr/bin/env python3
"""Outcome-sealed MovieLens-1M proof of concept for RAVEL.

RAVEL keeps the validation-selected linear semantic/collaborative ranker as an
exact default.  A uniform natural-pair, SimPO-derived bounded residual may act
only through a near-tie, linear-regret proposal and a validation-cross-fitted
selector.  Rejection returns the already materialized linear result byte for
byte.  Test labels are not read until every seed's target-blind test output
manifest has been exclusively published.

This module intentionally imports the audited CAPER primitives for temporal
splitting, SentenceTransformer encoding, BPR, FAISS retrieval, and append-only
artifact publication.  Both sources are hash-bound by the RAVEL protocol.
"""

from __future__ import annotations

import os

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
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import argparse
import csv
import hashlib
import importlib.metadata
import io
import json
import math
import platform
import shutil
import sys
import time
import traceback
import urllib.request
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import caper_poc as core

np = core.np
torch = core.torch


THREAD_ENVIRONMENT = core.THREAD_ENVIRONMENT
IntegrityError = core.IntegrityError
Interaction = core.Interaction
UserSplit = core.UserSplit
BPRArtifacts = core.BPRArtifacts
CandidateContext = core.CandidateContext
CandidateManifestEntry = core.CandidateManifestEntry
AlignmentCorpus = core.AlignmentCorpus
BoundedResidual = core.BoundedResidual


@dataclass(frozen=True)
class BinaryRouter:
    mean: np.ndarray
    scale: np.ndarray
    coefficient: np.ndarray
    intercept: float
    constant_probability: float | None
    training_rows: int

    def predict(self, features: np.ndarray) -> np.ndarray:
        matrix = np.asarray(features, dtype=np.float64)
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)
        if matrix.shape[1] != len(self.mean) or not np.all(np.isfinite(matrix)):
            raise IntegrityError("Invalid selector feature matrix")
        if self.constant_probability is not None:
            return np.full(len(matrix), self.constant_probability, dtype=np.float64)
        standardized = (matrix - self.mean) / self.scale
        logits = standardized @ self.coefficient + self.intercept
        logits = np.clip(logits, -40.0, 40.0)
        return 1.0 / (1.0 + np.exp(-logits))

    def serializable(self) -> Mapping[str, Any]:
        return {
            "mean": self.mean.tolist(),
            "scale": self.scale.tolist(),
            "coefficient": self.coefficient.tolist(),
            "intercept": self.intercept,
            "constant_probability": self.constant_probability,
            "training_rows": self.training_rows,
        }


@dataclass(frozen=True)
class RouterBundle:
    benefit: BinaryRouter
    harm: BinaryRouter
    single_head: BinaryRouter

    def serializable(self) -> Mapping[str, Any]:
        return {
            "benefit": self.benefit.serializable(),
            "harm": self.harm.serializable(),
            "single_head_selector_diagnostic": self.single_head.serializable(),
        }


@dataclass(frozen=True)
class LinearDefault:
    items: tuple[int, ...]
    ranking: tuple[int, ...]
    scores: np.ndarray
    bpr_scores: np.ndarray
    semantic_scores: np.ndarray
    features: np.ndarray


@dataclass(frozen=True)
class Proposal:
    ranking: tuple[int, ...]
    scores: np.ndarray
    descriptor: np.ndarray
    changed: bool
    linear_regret: float
    near_tie_fraction: float
    near_tie_tightness: float
    uncertainty_score: float
    swap_count: int
    fail_closed_reason: str | None


@dataclass(frozen=True)
class PolicyOutput:
    ranking: tuple[int, ...]
    scores: np.ndarray
    accepted: bool
    exact_fallback: bool


@dataclass(frozen=True)
class TestPolicyEntry:
    candidates: CandidateManifestEntry
    linear: LinearDefault
    proposal: Proposal
    always_on_proposal: Proposal
    outputs: Mapping[str, PolicyOutput]
    router_probabilities: Mapping[str, float]


class RunnerLock:
    """Exclusive RAVEL runner lock with one dead-owner retirement attempt."""

    def __init__(self, path: Path, protocol_hash: str) -> None:
        self.path = path
        self.protocol_hash = protocol_hash
        self.token = uuid.uuid4().hex
        self.acquired = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(2):
            try:
                core.publish_json_no_overwrite(
                    self.path,
                    {
                        "schema": "ravel-runner-lock-v1",
                        "pid": os.getpid(),
                        "token": self.token,
                        "protocol_sha256": self.protocol_hash,
                        "created_utc": core.utc_now(),
                    },
                )
                self.acquired = True
                return
            except FileExistsError:
                if attempt:
                    raise IntegrityError(f"Racing RAVEL runner lock: {self.path}")
                try:
                    existing = json.loads(self.path.read_text(encoding="utf-8"))
                    owner_pid = int(existing["pid"])
                    owner_token = str(existing["token"])
                except Exception as exc:
                    raise IntegrityError("Malformed RAVEL runner lock") from exc
                if not owner_token or core.process_is_alive(owner_pid):
                    raise IntegrityError(
                        f"RAVEL lock belongs to live PID {owner_pid}: {self.path}"
                    )
                retired = self.path.with_name(
                    f"{self.path.name}.retired."
                    f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}."
                    f"{uuid.uuid4().hex}.json"
                )
                try:
                    os.rename(self.path, retired)
                    core.fsync_directory(self.path.parent)
                except OSError as exc:
                    raise IntegrityError("RAVEL dead-lock retirement raced") from exc
        raise AssertionError("unreachable")

    def release(self) -> None:
        if not self.acquired:
            return
        current = json.loads(self.path.read_text(encoding="utf-8"))
        if current.get("token") != self.token or int(current.get("pid", -1)) != os.getpid():
            raise IntegrityError("RAVEL runner-lock ownership changed")
        self.path.unlink()
        core.fsync_directory(self.path.parent)
        self.acquired = False


def validate_config(config: Mapping[str, Any]) -> None:
    for section in (
        "dataset",
        "embedding",
        "retrieval",
        "bpr",
        "residual",
        "proposal",
        "selector",
        "evaluation",
        "promise_gate",
    ):
        if not isinstance(config.get(section), Mapping):
            raise ValueError(f"Missing configuration section: {section}")
    dataset = config["dataset"]
    seeds = [int(seed) for seed in config.get("replicate_seeds", [])]
    if len(seeds) != 3 or len(set(seeds)) != 3 or any(seed < 0 for seed in seeds):
        raise ValueError("Exactly three distinct nonnegative seeds are required")
    if [float(value) for value in dataset["split_fractions"]] != [0.6, 0.2, 0.1, 0.1]:
        raise ValueError("RAVEL requires the locked A/R/V/T 60/20/10/10 split")
    if dataset.get("split_unit") != "per-user indivisible timestamp groups":
        raise ValueError("Timestamp groups must remain indivisible")
    retrieval = config["retrieval"]
    if retrieval.get("index_kind") != "IndexFlatIP" or retrieval.get("metric") != "inner_product":
        raise ValueError("RAVEL PoC requires exact FAISS inner-product indexes")
    if (
        int(retrieval["collaborative_candidates"]) != 200
        or int(retrieval["semantic_candidates"]) != 200
        or int(retrieval["maximum_union_candidates"]) != 400
        or int(retrieval["collaborative_candidate_recall_k"]) != 200
        or int(retrieval["union_candidate_maximum_size"]) != 400
    ):
        raise ValueError("RAVEL requires B@200, S@200, and an untruncated C<=400")
    if int(dataset["minimum_heldout_preference_pairs"]) < 500:
        raise ValueError("The test preference cohort requires at least 500 pairs")
    if int(dataset["minimum_pair_bearing_test_users"]) < 300:
        raise ValueError("The test preference cohort requires at least 300 users")
    if int(dataset["minimum_alignment_natural_pairs"]) < 500:
        raise ValueError("Alignment requires at least 500 natural pairs")
    if int(dataset["minimum_alignment_pair_bearing_users"]) < 300:
        raise ValueError("Alignment requires at least 300 pair-bearing users")
    if (
        int(dataset["minimum_timestamp_groups"]) != 4
        or int(dataset["minimum_validation_positive_items"]) != 1
        or int(dataset["minimum_test_positive_items"]) != 1
    ):
        raise ValueError("Locked eligibility count floors changed")
    if config["bpr"].get("prefix_query_update") != (
        "trained_user_plus_rating_weighted_frozen_item_aggregate"
    ):
        raise ValueError("Unregistered BPR prefix update")
    if float(config["residual"]["residual_bound"]) <= 0.0:
        raise ValueError("Residual bound must be positive")
    if int(config["evaluation"]["bootstrap_repetitions"]) < 1000:
        raise ValueError("At least 1,000 bootstrap repetitions are required")
    if str(dataset.get("expected_sha256")) != (
        "a6898adb50b9ca05aa231689da44c217cb524e7ebd39d264c56e2832f2c54e20"
    ):
        raise ValueError("RAVEL requires the prospectively SHA-locked ML-1M archive")
    slices = (
        int(dataset["caper_slice_start"]),
        int(dataset["caper_slice_stop"]),
        int(dataset["ravel_slice_start"]),
        int(dataset["ravel_slice_stop"]),
    )
    if slices != (0, 1000, 1000, 2000):
        raise ValueError("RAVEL requires the disjoint ordered user slice [1000:2000]")
    if int(dataset["minimum_eligible_users_before_slice"]) < 2000:
        raise ValueError("At least 2,000 eligible users must exist before slicing")
    if dataset.get("maximum_users") is not None:
        raise ValueError("Eligibility must be derived before either user slice is taken")
    if config["residual"].get("alignment_sampling") != (
        "uniform_without_replacement_over_natural_union_pairs"
    ):
        raise ValueError("RAVEL requires uniform natural-pair residual training")
    if config["residual"].get("soft_anchor_kl_scope") != "linear_correct_pairs_only":
        raise ValueError("RAVEL anchors only pairs already correct under frozen linear")
    if bool(config["selector"].get("use_historical_label_reliability_features")):
        raise ValueError("Cycle-3 PoC registers label-free selector descriptors only")
    if int(config["selector"]["crossfit_folds"]) < 2:
        raise ValueError("Selector requires at least two user cross-fitting folds")
    tie_grid = [float(value) for value in config["proposal"]["near_tie_width_grid"]]
    regret_grid = [
        float(value) for value in config["proposal"]["linear_regret_budget_grid"]
    ]
    if not tie_grid or any(value <= 0.0 for value in tie_grid):
        raise ValueError("Near-tie width grid must be positive")
    if not regret_grid or any(value < 0.0 for value in regret_grid):
        raise ValueError("Linear-regret budget grid must be nonnegative")


def acquire_locked_archive(
    destination: Path,
    official_url: str,
    expected_sha256: str,
    local_source: Path | None,
) -> tuple[str, str]:
    """Copy a local authenticated archive or download the official one."""
    expected = expected_sha256.lower()
    if local_source is None:
        digest = core.acquire_official_zip(destination, official_url, expected)
        return digest, "official_download"
    source = local_source.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    source_digest = core.sha256_file(source)
    if source_digest != expected:
        raise IntegrityError(
            f"Local dataset SHA-256 mismatch: expected {expected}, got {source_digest}"
        )
    temporary = destination.with_name(
        f".{destination.name}.copy.{os.getpid()}.{uuid.uuid4().hex}"
    )
    try:
        with source.open("rb") as input_handle, temporary.open("xb") as output_handle:
            shutil.copyfileobj(input_handle, output_handle, length=1024 * 1024)
            output_handle.flush()
            os.fsync(output_handle.fileno())
        if core.sha256_file(temporary) != expected:
            raise IntegrityError("Copied local archive changed during acquisition")
        os.link(temporary, destination)
        core.fsync_directory(destination.parent)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return expected, "authenticated_local_copy"


def derive_ravel_cohort(
    interactions: Sequence[Interaction], dataset: Mapping[str, Any]
) -> tuple[list[UserSplit], Mapping[str, Any]]:
    all_dataset = dict(dataset)
    all_dataset["maximum_users"] = None
    all_dataset["minimum_test_users"] = int(dataset["minimum_eligible_users_before_slice"])
    eligible, split_diagnostics = core.chronological_timestamp_group_splits(
        interactions, all_dataset
    )
    subset_seed = int(dataset["stable_subset_seed"])
    ordered = sorted(
        eligible,
        key=lambda split: (
            hashlib.sha256(f"{subset_seed}:{split.user_id}".encode("ascii")).hexdigest(),
            split.user_id,
        ),
    )
    required = int(dataset["minimum_eligible_users_before_slice"])
    if len(ordered) < required:
        raise IntegrityError(f"Only {len(ordered)} eligible users; RAVEL requires {required}")
    caper = ordered[
        int(dataset["caper_slice_start"]) : int(dataset["caper_slice_stop"])
    ]
    ravel = ordered[
        int(dataset["ravel_slice_start"]) : int(dataset["ravel_slice_stop"])
    ]
    caper_ids = {split.user_id for split in caper}
    ravel_ids = {split.user_id for split in ravel}
    if len(caper) != 1000 or len(ravel) != 1000 or caper_ids & ravel_ids:
        raise IntegrityError("Prospective CAPER/RAVEL cohort disjointness failed")
    return sorted(ravel, key=lambda split: split.user_id), {
        **dict(split_diagnostics),
        "eligible_before_hash_slice": len(ordered),
        "ordering_key": f"SHA256({subset_seed}:user_id), then numeric user_id",
        "caper_slice": [0, 1000],
        "ravel_slice": [1000, 2000],
        "caper_user_ids_sha256": core.sha256_bytes(
            core.canonical_json_bytes(sorted(caper_ids))
        ),
        "ravel_user_ids_sha256": core.sha256_bytes(
            core.canonical_json_bytes(sorted(ravel_ids))
        ),
        "slice_intersection_count": len(caper_ids & ravel_ids),
        "cohorts_disjoint": True,
    }


def sealed_stage_views(
    splits: Sequence[UserSplit],
) -> tuple[list[UserSplit], list[UserSplit], list[UserSplit]]:
    """Remove future blocks structurally before entering target-blind stages."""
    a_only = [UserSplit(split.user_id, split.train, (), (), ()) for split in splits]
    a_plus_r = [
        UserSplit(split.user_id, split.train, split.alignment, (), ()) for split in splits
    ]
    a_plus_r_plus_v = [
        UserSplit(
            split.user_id,
            split.train,
            split.alignment,
            split.validation,
            (),
        )
        for split in splits
    ]
    return a_only, a_plus_r, a_plus_r_plus_v


def preference_pairs_by_movie_id(
    events: Sequence[Interaction],
    minimum_gap: int,
    maximum: int,
    subsample_seed: int,
    user_id: int,
    catalog_item_ids: Sequence[int],
) -> tuple[list[tuple[int, int]], int]:
    """Build natural pairs with the preregistered movie-ID hash cap."""
    pairs: list[tuple[int, int]] = []
    ordered = sorted(
        events,
        key=lambda event: (int(catalog_item_ids[event.item_index]), event.ordinal),
    )
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
                        f"{subsample_seed}:{user_id}:"
                        f"{min(int(catalog_item_ids[pair[0]]), int(catalog_item_ids[pair[1]]))}:"
                        f"{max(int(catalog_item_ids[pair[0]]), int(catalog_item_ids[pair[1]]))}"
                    ).encode("ascii")
                ).hexdigest(),
                pair,
            ),
        )[:maximum]
    return pairs, raw_count


def build_uniform_linear_corpus(
    splits: Sequence[UserSplit],
    manifest: Mapping[int, CandidateContext],
    bpr: BPRArtifacts,
    semantic_vectors: np.ndarray,
    popularity: np.ndarray,
    linear_alpha: float,
    config: Mapping[str, Any],
    seed: int,
    catalog_item_ids: Sequence[int],
    registered_pair_keys: frozenset[tuple[int, int, int]],
) -> AlignmentCorpus:
    """Join R only after its manifest and sample natural pairs uniformly."""
    rows: list[
        tuple[np.ndarray, np.ndarray, float, float, int, bool, int, int]
    ] = []
    pair_users: set[int] = set()
    gap_min = int(config["dataset"]["preference_pair_minimum_rating_gap"])
    for split in splits:
        context = manifest[split.user_id]
        ratings = {
            event.item_index: event.rating
            for event in split.alignment
            if event.item_index in context.union
        }
        items = sorted(ratings)
        user_rows = 0
        for left in range(len(items)):
            for right in range(left + 1, len(items)):
                gap = ratings[items[left]] - ratings[items[right]]
                if abs(gap) < gap_min:
                    continue
                chosen, rejected = (
                    (items[left], items[right]) if gap > 0 else (items[right], items[left])
                )
                caper_features, base, semantic = core.item_features(
                    context,
                    [chosen, rejected],
                    bpr,
                    semantic_vectors,
                    popularity,
                    config["retrieval"],
                )
                linear = linear_alpha * base + (1.0 - linear_alpha) * semantic
                features = ravel_item_features(caper_features, linear)
                rows.append(
                    (
                        features[0].copy(),
                        features[1].copy(),
                        float(linear[0]),
                        float(linear[1]),
                        split.user_id,
                        bool(linear[0] <= linear[1]),
                        chosen,
                        rejected,
                    )
                )
                user_rows += 1
        if user_rows:
            pair_users.add(split.user_id)
    if len(rows) < int(config["dataset"]["minimum_alignment_natural_pairs"]):
        raise IntegrityError("Alignment contains too few natural union-present pairs")
    if len(pair_users) < int(config["dataset"]["minimum_alignment_pair_bearing_users"]):
        raise IntegrityError("Alignment contains too few pair-bearing users")
    rebuilt_keys = frozenset((row[4], row[6], row[7]) for row in rows)
    if rebuilt_keys != registered_pair_keys:
        raise IntegrityError("Residual pair pool differs from the pre-published R pool")
    count = min(len(rows), int(config["residual"]["maximum_alignment_pairs"]))
    selected = sorted(
        rows,
        key=lambda row: (
            hashlib.sha256(
                (
                    f"ravel-R-pair-v1:{seed}:{row[4]}:"
                    f"{min(catalog_item_ids[row[6]], catalog_item_ids[row[7]])}:"
                    f"{max(catalog_item_ids[row[6]], catalog_item_ids[row[7]])}"
                ).encode("ascii")
            ).hexdigest(),
            row[4],
            min(catalog_item_ids[row[6]], catalog_item_ids[row[7]]),
            max(catalog_item_ids[row[6]], catalog_item_ids[row[7]]),
        ),
    )[:count]
    return AlignmentCorpus(
        chosen_features=np.stack([row[0] for row in selected]).astype(np.float32),
        rejected_features=np.stack([row[1] for row in selected]).astype(np.float32),
        chosen_base_scores=np.asarray([row[2] for row in selected], dtype=np.float32),
        rejected_base_scores=np.asarray([row[3] for row in selected], dtype=np.float32),
        user_ids=np.asarray([row[4] for row in selected], dtype=np.int64),
        contradiction_mask=np.asarray([row[5] for row in selected], dtype=np.bool_),
        diagnostics={
            "schedule": "uniform_without_replacement_over_natural_union_pairs",
            "raw_natural_pairs": len(rows),
            "selected_pairs": len(selected),
            "replacement_duplicates": 0,
            "cap_order": "SHA256(ravel-R-pair-v1:seed:user:low_item:high_item)",
            "users_with_natural_pairs": len(pair_users),
            "base_score": "frozen_validation_selected_linear_fusion",
            "all_pairs_are_natural_and_union_present": True,
            "targets_injected": False,
        },
    )


def build_alignment_pair_pool(
    splits: Sequence[UserSplit],
    manifest: Mapping[int, CandidateContext],
    minimum_gap: int,
    catalog_item_ids: Sequence[int],
) -> tuple[frozenset[tuple[int, int, int]], list[Mapping[str, Any]]]:
    keys: set[tuple[int, int, int]] = set()
    serializable: list[Mapping[str, Any]] = []
    for split in splits:
        context = manifest[split.user_id]
        ratings = {
            event.item_index: event.rating
            for event in split.alignment
            if event.item_index in context.union
        }
        items = sorted(ratings)
        for left in range(len(items)):
            for right in range(left + 1, len(items)):
                gap = ratings[items[left]] - ratings[items[right]]
                if abs(gap) < minimum_gap:
                    continue
                chosen, rejected = (
                    (items[left], items[right]) if gap > 0 else (items[right], items[left])
                )
                key = (split.user_id, chosen, rejected)
                if key in keys:
                    raise IntegrityError("Duplicate natural R pair")
                keys.add(key)
                serializable.append(
                    {
                        "user_id": split.user_id,
                        "chosen_item_index": chosen,
                        "rejected_item_index": rejected,
                        "chosen_movie_id": int(catalog_item_ids[chosen]),
                        "rejected_movie_id": int(catalog_item_ids[rejected]),
                        "absolute_rating_gap": abs(gap),
                        "both_naturally_present_in_published_union": True,
                        "target_injected": False,
                    }
                )
    return frozenset(keys), serializable


def ravel_item_features(
    caper_features: np.ndarray, linear_scores: np.ndarray
) -> np.ndarray:
    """Reorder CAPER scalars into the locked 13-input RAVEL feature vector."""
    source = np.asarray(caper_features, dtype=np.float32)
    linear = np.asarray(linear_scores, dtype=np.float32).reshape(-1)
    features = np.stack(
        (
            source[:, 1],
            source[:, 0],
            linear,
            source[:, 2],
            source[:, 1] - source[:, 0],
            source[:, 4],
            source[:, 5],
            source[:, 6],
            source[:, 7],
            source[:, 8],
            source[:, 9],
            source[:, 10],
            source[:, 11],
        ),
        axis=1,
    ).astype(np.float32, copy=False)
    if features.shape[1] != 13 or not np.all(np.isfinite(features)):
        raise IntegrityError("Invalid locked RAVEL item feature matrix")
    return features


def materialize_linear_default(
    context: CandidateContext,
    bpr: BPRArtifacts,
    semantic_vectors: np.ndarray,
    popularity: np.ndarray,
    linear_alpha: float,
    config: Mapping[str, Any],
) -> LinearDefault:
    caper_features, base, semantic = core.item_features(
        context,
        context.union,
        bpr,
        semantic_vectors,
        popularity,
        config["retrieval"],
    )
    scores = np.ascontiguousarray(
        linear_alpha * base + (1.0 - linear_alpha) * semantic, dtype=np.float32
    )
    features = np.ascontiguousarray(
        ravel_item_features(caper_features, scores), dtype=np.float32
    )
    ranking, _diagnostics = core.hard_regret_projection(
        context.union,
        scores,
        base,
        int(config["residual"]["projection_k"]),
        float(config["residual"]["hard_cumulative_normalized_bpr_regret_budget"]),
        context.regret_scale_degenerate,
    )
    return LinearDefault(
        items=tuple(context.union),
        ranking=tuple(ranking),
        scores=scores,
        bpr_scores=np.ascontiguousarray(base, dtype=np.float32),
        semantic_scores=np.ascontiguousarray(semantic, dtype=np.float32),
        features=np.ascontiguousarray(features, dtype=np.float32),
    )


def _priority_topological_order(
    selected: set[int],
    items: Sequence[int],
    adjusted_by_item: Mapping[int, float],
    linear_by_item: Mapping[int, float],
    linear_rank: Mapping[int, int],
    protected_gap: float,
) -> list[int]:
    outgoing: dict[int, set[int]] = {item: set() for item in selected}
    indegree: dict[int, int] = {item: 0 for item in selected}
    for left in selected:
        for right in selected:
            if left == right:
                continue
            if linear_by_item[left] > linear_by_item[right] + protected_gap:
                if right not in outgoing[left]:
                    outgoing[left].add(right)
                    indegree[right] += 1
    ready = [item for item in selected if indegree[item] == 0]
    result: list[int] = []
    while ready:
        chosen = min(
            ready,
            key=lambda item: (
                -adjusted_by_item[item],
                linear_rank.get(item, len(items)),
                item,
            ),
        )
        ready.remove(chosen)
        result.append(chosen)
        for child in sorted(outgoing[chosen]):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
    if len(result) != len(selected):
        raise IntegrityError("Near-tie precedence graph contains a cycle")
    return result


def make_proposal(
    linear: LinearDefault,
    residual_values: np.ndarray,
    tie_width: float,
    regret_budget: float,
    config: Mapping[str, Any],
) -> Proposal:
    """Create a near-tie proposal anchored to the exact linear default."""
    items = linear.items
    k = int(config["proposal"]["projection_k"])
    if len(items) < k or len(residual_values) != len(items):
        raise IntegrityError("Invalid proposal inputs")
    linear_scores = np.asarray(linear.scores, dtype=np.float64)
    residual = np.asarray(residual_values, dtype=np.float64) * float(
        config["residual"]["residual_scale"]
    )
    lower, upper = np.quantile(
        linear_scores,
        [
            float(config["proposal"]["linear_score_scale_lower_quantile"]),
            float(config["proposal"]["linear_score_scale_upper_quantile"]),
        ],
    )
    raw_scale = float(upper - lower)
    scale = max(raw_scale, float(config["proposal"]["linear_score_scale_floor"]))
    default_top = list(linear.ranking[:k])
    index_by_item = {item: index for index, item in enumerate(items)}
    linear_by_item = {item: float(linear_scores[index]) for index, item in enumerate(items)}
    default_score_values = np.asarray(
        [linear_by_item[item] for item in default_top], dtype=np.float64
    )
    normalized_distance = np.asarray(
        [
            min(abs(float(score) - float(reference)) for reference in default_score_values)
            / scale
            for score in linear_scores
        ],
        dtype=np.float64,
    )
    eligible = normalized_distance <= tie_width + 1e-12
    # The adjusted score exists for every item in the immutable union. Near-tie
    # eligibility limits top-10 intervention authority, not tail scoring or
    # whole-union residual descriptors.
    adjusted = linear_scores + residual
    adjusted_by_item = {
        item: float(adjusted[index]) for index, item in enumerate(items)
    }
    residual_by_item = {item: float(residual[index]) for index, item in enumerate(items)}
    linear_rank = {item: rank for rank, item in enumerate(linear.ranking)}
    top_twenty = np.asarray(
        [linear_by_item[item] / scale for item in linear.ranking[:20]],
        dtype=np.float64,
    )
    top_twenty -= float(np.max(top_twenty))
    probabilities = np.exp(top_twenty)
    probabilities /= float(np.sum(probabilities))
    uncertainty = float(-np.sum(probabilities * np.log(np.maximum(probabilities, 1e-15))))
    sign_checks: list[bool] = []
    for incoming in items:
        if incoming in default_top or not eligible[index_by_item[incoming]]:
            continue
        for outgoing in default_top:
            if abs(linear_by_item[incoming] - linear_by_item[outgoing]) / scale > tie_width:
                continue
            residual_advantage = residual_by_item[incoming] - residual_by_item[outgoing]
            adjusted_gain = adjusted_by_item[incoming] - adjusted_by_item[outgoing]
            sign_checks.append(
                (residual_advantage == 0.0 and adjusted_gain == 0.0)
                or residual_advantage * adjusted_gain > 0.0
            )
    sign_agreement = float(np.mean(sign_checks)) if sign_checks else 0.0
    if raw_scale <= float(config["proposal"]["linear_score_scale_floor"]):
        descriptor = request_descriptor(
            linear,
            adjusted,
            eligible,
            0,
            0.0,
            scale,
            regret_budget,
            0.0,
            0.0,
            default_top,
        )
        return Proposal(
            ranking=linear.ranking,
            scores=np.ascontiguousarray(linear.scores.copy()),
            descriptor=descriptor,
            changed=False,
            linear_regret=0.0,
            near_tie_fraction=float(np.mean(eligible)),
            near_tie_tightness=0.0,
            uncertainty_score=uncertainty,
            swap_count=0,
            fail_closed_reason="degenerate_linear_scale",
        )
    selected = set(default_top)
    touched: set[int] = set()
    default_sum = sum(linear_by_item[item] for item in default_top)
    proposal_order = sorted(
        items, key=lambda item: (-adjusted_by_item[item], linear_rank[item], item)
    )
    swaps = 0
    committed_normalized_gaps: list[float] = []
    committed_adjusted_gains: list[float] = []
    swap_candidates: list[tuple[float, int, int, float]] = []
    for incoming in items:
        if incoming in selected or not eligible[index_by_item[incoming]]:
            continue
        for outgoing in default_top:
            normalized_gap = abs(
                linear_by_item[incoming] - linear_by_item[outgoing]
            ) / scale
            adjusted_gain = adjusted_by_item[incoming] - adjusted_by_item[outgoing]
            residual_advantage = residual_by_item[incoming] - residual_by_item[outgoing]
            if normalized_gap > tie_width + 1e-12:
                continue
            if residual_advantage <= 0.0 or adjusted_gain <= 0.0:
                continue
            swap_candidates.append(
                (-float(adjusted_gain), int(incoming), int(outgoing), float(normalized_gap))
            )
    for negative_gain, incoming, outgoing, normalized_gap in sorted(swap_candidates):
        if incoming in selected or outgoing not in selected:
            continue
        if incoming in touched or outgoing in touched:
            continue
        tentative = selected - {outgoing} | {incoming}
        regret = max(
            0.0,
            (default_sum - sum(linear_by_item[item] for item in tentative)) / scale,
        )
        if regret <= regret_budget + 1e-9:
            selected = tentative
            touched.add(incoming)
            touched.add(outgoing)
            swaps += 1
            committed_normalized_gaps.append(normalized_gap)
            committed_adjusted_gains.append(-negative_gain)
    final_regret = max(
        0.0,
        (default_sum - sum(linear_by_item[item] for item in selected)) / scale,
    )
    try:
        top = _priority_topological_order(
            selected,
            items,
            adjusted_by_item,
            linear_by_item,
            linear_rank,
            tie_width * scale,
        )
        # A finite near-tie proposal may change only the constrained top-10
        # intervention.  Its nonselected tail retains the frozen linear order,
        # so full-order preference credit cannot come from unconstrained tail
        # inversions.  Infinite-width proposals are retained only as a local
        # implementation diagnostic, not as a registered gate comparator.
        tail_source = proposal_order if math.isinf(tie_width) else linear.ranking
        tail = [item for item in tail_source if item not in selected]
        ranking = tuple(top + tail)
        if final_regret > regret_budget + 1e-7:
            raise IntegrityError("Linear-anchor proposal exceeded its regret budget")
        changed = tuple(ranking[:k]) != tuple(linear.ranking[:k])
        fail_reason = None
    except IntegrityError as exc:
        ranking = linear.ranking
        adjusted = np.asarray(linear.scores, dtype=np.float64).copy()
        swaps = 0
        committed_normalized_gaps = []
        committed_adjusted_gains = []
        final_regret = 0.0
        changed = False
        fail_reason = str(exc)
    descriptor = request_descriptor(
        linear,
        adjusted,
        eligible,
        swaps,
        final_regret,
        scale,
        regret_budget,
        sign_agreement if swaps > 0 else 0.0,
        float(sum(committed_adjusted_gains)),
        ranking[:k],
    )
    return Proposal(
        ranking=ranking,
        scores=np.ascontiguousarray(adjusted, dtype=np.float32),
        descriptor=descriptor,
        changed=changed,
        linear_regret=float(final_regret),
        near_tie_fraction=float(np.mean(eligible)),
        near_tie_tightness=(
            float(max(committed_normalized_gaps)) if committed_normalized_gaps else 0.0
        ),
        uncertainty_score=uncertainty,
        swap_count=swaps,
        fail_closed_reason=fail_reason,
    )


def request_descriptor(
    linear: LinearDefault,
    adjusted_scores: np.ndarray,
    eligible: np.ndarray,
    swap_count: int,
    regret: float,
    linear_scale: float,
    regret_budget: float,
    sign_agreement: float,
    total_adjusted_gain: float,
    proposed_top: Sequence[int],
) -> np.ndarray:
    items = linear.items
    index = {item: position for position, item in enumerate(items)}
    default_top = tuple(linear.ranking[:10])
    proposed_top_tuple = tuple(proposed_top)
    default_set = set(default_top)
    proposed_set = set(proposed_top_tuple)
    union_size = len(default_set | proposed_set)
    overlap = (
        len(default_set & proposed_set) / union_size if union_size else 0.0
    )
    residual = np.asarray(adjusted_scores, dtype=np.float64) - np.asarray(
        linear.scores, dtype=np.float64
    )
    branch_overlap = float(
        np.mean((linear.features[:, 7] > 0.5) & (linear.features[:, 8] > 0.5))
    )
    semantic_only_top_fraction = float(
        np.mean(
            [
                linear.features[index[item], 8] > 0.5
                and linear.features[index[item], 7] <= 0.5
                for item in default_top
            ]
        )
    )
    boundary_gap = float(
        abs(
            float(linear.scores[index[linear.ranking[9]]])
            - float(linear.scores[index[linear.ranking[10]]])
        )
    )
    common = [item for item in default_top if item in set(proposed_top_tuple)]
    default_rank = {item: position for position, item in enumerate(default_top)}
    proposal_rank = {item: position for position, item in enumerate(proposed_top_tuple)}
    disagreements = 0
    comparisons = 0
    for left in range(len(common)):
        for right in range(left + 1, len(common)):
            first, second = common[left], common[right]
            comparisons += 1
            disagreements += int(
                (default_rank[first] - default_rank[second])
                * (proposal_rank[first] - proposal_rank[second])
                < 0
            )
    rank_disagreement = disagreements / comparisons if comparisons else 0.0
    descriptor = np.asarray(
        [
            float(linear.features[0, 11] * 8.0),
            len(items) / 400.0,
            branch_overlap,
            semantic_only_top_fraction,
            boundary_gap / linear_scale,
            float(np.mean(eligible)),
            float(swap_count),
            overlap,
            float(rank_disagreement),
            float(np.mean(np.abs(residual))),
            float(np.max(np.abs(residual))),
            float(sign_agreement),
            float(regret / max(regret_budget, 1e-12)),
            float(total_adjusted_gain / linear_scale),
        ],
        dtype=np.float64,
    )
    if not np.all(np.isfinite(descriptor)):
        raise IntegrityError("Selector descriptor contains nonfinite values")
    return descriptor


def fit_binary_router(
    features: np.ndarray, labels: np.ndarray, selector: Mapping[str, Any]
) -> BinaryRouter:
    matrix = np.asarray(features, dtype=np.float64)
    target = np.asarray(labels, dtype=np.int64)
    if matrix.ndim != 2 or len(matrix) != len(target) or not len(matrix):
        raise IntegrityError("Router training set is empty or malformed")
    if not np.all(np.isfinite(matrix)) or not set(np.unique(target)).issubset({0, 1}):
        raise IntegrityError("Router training values are invalid")
    mean = np.mean(matrix, axis=0)
    scale = np.std(matrix, axis=0)
    scale[scale < 1e-8] = 1.0
    unique = np.unique(target)
    if len(unique) == 1:
        raise IntegrityError(
            "Selector fold lacks both classes; refusing a constant-router fallback"
        )
    try:
        from sklearn.linear_model import LogisticRegression
    except ImportError as exc:
        raise RuntimeError("scikit-learn is required for RAVEL's selector") from exc
    standardized = (matrix - mean) / scale
    model = LogisticRegression(
        C=1.0 / max(float(selector["l2_regularization"]), 1e-12),
        solver="lbfgs",
        max_iter=int(selector["maximum_iterations"]),
        random_state=int(selector["deterministic_fold_seed"]),
        class_weight="balanced",
    )
    model.fit(standardized, target)
    if int(model.n_iter_[0]) >= int(selector["maximum_iterations"]):
        raise IntegrityError("Selector logistic fit did not converge")
    return BinaryRouter(
        mean=np.asarray(mean, dtype=np.float64),
        scale=np.asarray(scale, dtype=np.float64),
        coefficient=np.asarray(model.coef_[0], dtype=np.float64),
        intercept=float(model.intercept_[0]),
        constant_probability=None,
        training_rows=len(matrix),
    )


def _fold_for_user(user_id: int, selector: Mapping[str, Any]) -> int:
    digest = hashlib.sha256(
        f"{selector['deterministic_fold_seed']}:{user_id}".encode("ascii")
    ).hexdigest()
    return int(digest, 16) % int(selector["crossfit_folds"])


def crossfit_router(
    records: Sequence[Mapping[str, Any]], selector: Mapping[str, Any]
) -> tuple[Mapping[tuple[int, int], Mapping[str, float]], Mapping[str, Any]]:
    features = np.stack([np.asarray(row["descriptor"], dtype=np.float64) for row in records])
    users = np.asarray([int(row["user_id"]) for row in records], dtype=np.int64)
    folds = np.asarray([_fold_for_user(int(user), selector) for user in users])
    preference_delta = np.asarray(
        [float(row["preference_delta"]) for row in records], dtype=np.float64
    )
    harmful = np.asarray([bool(row["harmful"]) for row in records], dtype=np.int64)
    benefit_prediction = np.full(len(records), np.nan, dtype=np.float64)
    harm_prediction = np.full(len(records), np.nan, dtype=np.float64)
    single_head_prediction = np.full(len(records), np.nan, dtype=np.float64)
    fold_diagnostics: list[Mapping[str, Any]] = []
    for fold in range(int(selector["crossfit_folds"])):
        heldout = folds == fold
        training = ~heldout
        benefit_training = training & np.isfinite(preference_delta)
        if not np.any(heldout) or not np.any(training) or not np.any(benefit_training):
            raise IntegrityError("A selector cross-fitting fold is empty")
        benefit_model = fit_binary_router(
            features[benefit_training],
            (preference_delta[benefit_training] > 0.0).astype(np.int64),
            selector,
        )
        harm_model = fit_binary_router(features[training], harmful[training], selector)
        single_head_labels = (
            np.isfinite(preference_delta[benefit_training])
            & (preference_delta[benefit_training] > 0.0)
            & (harmful[benefit_training] == 0)
        ).astype(np.int64)
        single_head_model = fit_binary_router(
            features[benefit_training], single_head_labels, selector
        )
        benefit_prediction[heldout] = benefit_model.predict(features[heldout])
        harm_prediction[heldout] = harm_model.predict(features[heldout])
        single_head_prediction[heldout] = single_head_model.predict(features[heldout])
        fold_diagnostics.append(
            {
                "fold": fold,
                "training_users": int(np.sum(training)),
                "benefit_training_users": int(np.sum(benefit_training)),
                "heldout_users": int(np.sum(heldout)),
            }
        )
    if not (
        np.all(np.isfinite(benefit_prediction))
        and np.all(np.isfinite(harm_prediction))
        and np.all(np.isfinite(single_head_prediction))
    ):
        raise IntegrityError("Cross-fitted selector predictions are incomplete")
    predictions = {
        (int(row.get("seed", 0)), int(row["user_id"])): {
            "benefit_probability": float(benefit_prediction[index]),
            "harm_probability": float(harm_prediction[index]),
            "single_head_probability": float(single_head_prediction[index]),
        }
        for index, row in enumerate(records)
    }
    return predictions, {
        "folds": fold_diagnostics,
        "heldout_predictions_only": True,
        "standardization_fit_inside_each_training_fold": True,
    }


def fit_full_router(
    records: Sequence[Mapping[str, Any]], selector: Mapping[str, Any]
) -> RouterBundle:
    features = np.stack([np.asarray(row["descriptor"], dtype=np.float64) for row in records])
    preference_delta = np.asarray(
        [float(row["preference_delta"]) for row in records], dtype=np.float64
    )
    harmful = np.asarray([bool(row["harmful"]) for row in records], dtype=np.int64)
    pair_mask = np.isfinite(preference_delta)
    if not np.any(pair_mask):
        raise IntegrityError("No validation pair users for final selector fit")
    benefit_labels = (preference_delta[pair_mask] > 0.0).astype(np.int64)
    single_head_labels = (
        (preference_delta[pair_mask] > 0.0) & (harmful[pair_mask] == 0)
    ).astype(np.int64)
    return RouterBundle(
        benefit=fit_binary_router(features[pair_mask], benefit_labels, selector),
        harm=fit_binary_router(features, harmful, selector),
        single_head=fit_binary_router(features[pair_mask], single_head_labels, selector),
    )


def _pair_accuracy(
    pairs: Sequence[tuple[int, int]], ranking: Sequence[int]
) -> tuple[float, float]:
    if not pairs:
        return float("nan"), 0.0
    rank = {int(item): position for position, item in enumerate(ranking)}
    correct = 0.0
    for chosen, rejected in pairs:
        if chosen not in rank or rejected not in rank:
            raise IntegrityError("Preference pair is absent from the served full ranking")
        correct += 1.0 if rank[chosen] < rank[rejected] else 0.0
    return float(correct / len(pairs)), float(correct)


def validation_bpr_metrics(
    splits: Sequence[UserSplit],
    manifest: Mapping[int, CandidateContext],
    config: Mapping[str, Any],
) -> Mapping[str, float]:
    ndcg: list[float] = []
    recall: list[float] = []
    positive_min = int(config["dataset"]["positive_rating_min"])
    for split in splits:
        targets = frozenset(
            event.item_index
            for event in split.validation
            if event.rating >= positive_min
        )
        ranking = manifest[split.user_id].collaborative
        ndcg.append(core.binary_ndcg(ranking, targets, 10))
        recall.append(core.recall_at_k(ranking, targets, 10))
    return {"ndcg_at_10": float(np.mean(ndcg)), "recall_at_10": float(np.mean(recall))}


def validation_linear_grid_metrics(
    splits: Sequence[UserSplit],
    manifest: Mapping[int, CandidateContext],
    bpr: BPRArtifacts,
    semantic_vectors: np.ndarray,
    popularity: np.ndarray,
    config: Mapping[str, Any],
) -> Mapping[str, Mapping[str, float]]:
    grid = [float(value) for value in config["residual"]["linear_fusion_validation_grid"]]
    values: dict[str, dict[str, list[float]]] = {
        str(value): {"ndcg": [], "recall": []} for value in grid
    }
    for split in splits:
        context = manifest[split.user_id]
        _features, base, semantic = core.item_features(
            context,
            context.union,
            bpr,
            semantic_vectors,
            popularity,
            config["retrieval"],
        )
        targets = frozenset(
            event.item_index
            for event in split.validation
            if event.rating >= int(config["dataset"]["positive_rating_min"])
        )
        for value in grid:
            scores = value * base + (1.0 - value) * semantic
            ranking, _diagnostics = core.hard_regret_projection(
                context.union,
                scores,
                base,
                int(config["residual"]["projection_k"]),
                float(config["residual"]["hard_cumulative_normalized_bpr_regret_budget"]),
                context.regret_scale_degenerate,
            )
            values[str(value)]["ndcg"].append(core.binary_ndcg(ranking, targets, 10))
            values[str(value)]["recall"].append(core.recall_at_k(ranking, targets, 10))
    return {
        key: {
            "ndcg_at_10": float(np.mean(metrics["ndcg"])),
            "recall_at_10": float(np.mean(metrics["recall"])),
        }
        for key, metrics in values.items()
    }


def validation_records(
    splits: Sequence[UserSplit],
    manifest: Mapping[int, CandidateContext],
    bpr: BPRArtifacts,
    semantic_vectors: np.ndarray,
    popularity: np.ndarray,
    residual_model: BoundedResidual,
    linear_alpha: float,
    tie_width: float,
    regret_budget: float,
    config: Mapping[str, Any],
    catalog_item_ids: Sequence[int],
) -> list[Mapping[str, Any]]:
    """Open V outcomes only after every V manifest has been published."""
    result: list[Mapping[str, Any]] = []
    positive_min = int(config["dataset"]["positive_rating_min"])
    for split in splits:
        context = manifest[split.user_id]
        linear = materialize_linear_default(
            context, bpr, semantic_vectors, popularity, linear_alpha, config
        )
        residual = core.residual_numpy(residual_model, linear.features)
        proposal = make_proposal(
            linear, residual, tie_width, regret_budget, config
        )
        targets = frozenset(
            event.item_index
            for event in split.validation
            if event.rating >= positive_min
        )
        pairs, _raw_count = preference_pairs_by_movie_id(
            [event for event in split.validation if event.item_index in context.union],
            int(config["dataset"]["preference_pair_minimum_rating_gap"]),
            int(config["evaluation"]["maximum_preference_pairs_per_user"]),
            int(config["evaluation"]["preference_pair_subsample_seed"]),
            split.user_id,
            catalog_item_ids,
        )
        linear_accuracy, _linear_correct = _pair_accuracy(
            pairs, linear.ranking
        )
        proposal_accuracy, _proposal_correct = _pair_accuracy(
            pairs, proposal.ranking
        )
        linear_ndcg = core.binary_ndcg(
            linear.ranking, targets, int(config["evaluation"]["ndcg_k"])
        )
        proposal_ndcg = core.binary_ndcg(
            proposal.ranking, targets, int(config["evaluation"]["ndcg_k"])
        )
        preference_delta = (
            proposal_accuracy - linear_accuracy
            if math.isfinite(linear_accuracy) and math.isfinite(proposal_accuracy)
            else float("nan")
        )
        result.append(
            {
                "user_id": split.user_id,
                "descriptor": proposal.descriptor,
                "proposal_changed": proposal.changed,
                "near_tie_fraction": proposal.near_tie_fraction,
                "near_tie_tightness": proposal.near_tie_tightness,
                "uncertainty_score": proposal.uncertainty_score,
                "linear_regret": proposal.linear_regret,
                "preference_pairs": len(pairs),
                "linear_preference_accuracy": linear_accuracy,
                "proposal_preference_accuracy": proposal_accuracy,
                "preference_delta": preference_delta,
                "linear_ndcg": linear_ndcg,
                "proposal_ndcg": proposal_ndcg,
                "ndcg_delta": proposal_ndcg - linear_ndcg,
                "harmful": proposal_ndcg < linear_ndcg,
            }
        )
    return result


def build_validation_proposal_rows(
    splits: Sequence[UserSplit],
    manifest: Mapping[int, CandidateContext],
    bpr: BPRArtifacts,
    semantic_vectors: np.ndarray,
    popularity: np.ndarray,
    residual_model: BoundedResidual,
    linear_alpha: float,
    tie_width: float,
    regret_budget: float,
    config: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    """Build V proposals and descriptors without receiving a V target object."""
    rows: list[Mapping[str, Any]] = []
    for split in splits:
        context = manifest[split.user_id]
        linear = materialize_linear_default(
            context, bpr, semantic_vectors, popularity, linear_alpha, config
        )
        residual = core.residual_numpy(residual_model, linear.features)
        proposal = make_proposal(linear, residual, tie_width, regret_budget, config)
        rows.append(
            {
                "user_id": split.user_id,
                "context": context,
                "linear": linear,
                "proposal": proposal,
                "descriptor": proposal.descriptor,
                "proposal_changed": proposal.changed,
                "near_tie_fraction": proposal.near_tie_fraction,
                "near_tie_tightness": proposal.near_tie_tightness,
                "uncertainty_score": proposal.uncertainty_score,
                "linear_regret": proposal.linear_regret,
            }
        )
    return rows


def serialize_validation_proposal_rows(
    rows: Sequence[Mapping[str, Any]], tie_width: float, regret_budget: float
) -> list[Mapping[str, Any]]:
    serializable: list[Mapping[str, Any]] = []
    for row in rows:
        context: CandidateContext = row["context"]
        linear: LinearDefault = row["linear"]
        proposal: Proposal = row["proposal"]
        serializable.append(
            {
                "user_id": row["user_id"],
                "tie_width": tie_width if math.isfinite(tie_width) else "infinity",
                "linear_regret_budget": regret_budget,
                "union_items": list(context.union),
                "linear_full_union_ranking": list(linear.ranking),
                "linear_union_score_bits_by_union_item": [
                    np.asarray(value, dtype="<f4").tobytes().hex()
                    for value in linear.scores
                ],
                "proposal_full_union_ranking": list(proposal.ranking),
                "proposal_union_score_bits_by_union_item": [
                    np.asarray(value, dtype="<f4").tobytes().hex()
                    for value in proposal.scores
                ],
                "descriptor": proposal.descriptor.tolist(),
                "proposal_changed": proposal.changed,
                "near_tie_tightness": proposal.near_tie_tightness,
                "uncertainty_entropy": proposal.uncertainty_score,
                "linear_regret": proposal.linear_regret,
                "V_labels_joined": False,
            }
        )
    return serializable


def join_validation_proposal_outcomes(
    splits: Sequence[UserSplit],
    proposal_rows: Sequence[Mapping[str, Any]],
    config: Mapping[str, Any],
    catalog_item_ids: Sequence[int],
) -> list[Mapping[str, Any]]:
    """Join V once proposal rows have already been exclusively published."""
    split_by_user = {split.user_id: split for split in splits}
    result: list[Mapping[str, Any]] = []
    for target_blind in proposal_rows:
        user_id = int(target_blind["user_id"])
        split = split_by_user[user_id]
        context: CandidateContext = target_blind["context"]
        linear: LinearDefault = target_blind["linear"]
        proposal: Proposal = target_blind["proposal"]
        targets = frozenset(
            event.item_index
            for event in split.validation
            if event.rating >= int(config["dataset"]["positive_rating_min"])
        )
        pairs, raw_pair_count = preference_pairs_by_movie_id(
            [event for event in split.validation if event.item_index in context.union],
            int(config["dataset"]["preference_pair_minimum_rating_gap"]),
            int(config["evaluation"]["maximum_preference_pairs_per_user"]),
            int(config["evaluation"]["preference_pair_subsample_seed"]),
            user_id,
            catalog_item_ids,
        )
        linear_accuracy, _ = _pair_accuracy(pairs, linear.ranking)
        proposal_accuracy, _ = _pair_accuracy(pairs, proposal.ranking)
        linear_ndcg = core.binary_ndcg(linear.ranking, targets, 10)
        proposal_ndcg = core.binary_ndcg(proposal.ranking, targets, 10)
        preference_delta = (
            proposal_accuracy - linear_accuracy
            if math.isfinite(linear_accuracy) and math.isfinite(proposal_accuracy)
            else float("nan")
        )
        result.append(
            {
                "user_id": user_id,
                "descriptor": target_blind["descriptor"],
                "proposal_changed": target_blind["proposal_changed"],
                "near_tie_fraction": target_blind["near_tie_fraction"],
                "near_tie_tightness": target_blind["near_tie_tightness"],
                "uncertainty_score": target_blind["uncertainty_score"],
                "linear_regret": target_blind["linear_regret"],
                "preference_pairs": len(pairs),
                "raw_preference_pairs_before_hash_cap": raw_pair_count,
                "linear_preference_accuracy": linear_accuracy,
                "proposal_preference_accuracy": proposal_accuracy,
                "preference_delta": preference_delta,
                "linear_ndcg": linear_ndcg,
                "proposal_ndcg": proposal_ndcg,
                "ndcg_delta": proposal_ndcg - linear_ndcg,
                "harmful": proposal_ndcg < linear_ndcg,
            }
        )
    return result


def proposal_spec_key(tie_width: float, regret_budget: float) -> str:
    return f"tie={tie_width:.12g}|linear_regret={regret_budget:.12g}"


def select_validation_policy(
    records_by_seed_spec: Mapping[int, Mapping[str, Sequence[Mapping[str, Any]]]],
    oof_by_seed_spec: Mapping[int, Mapping[str, Mapping[Any, Mapping[str, float]]]],
    config: Mapping[str, Any],
) -> Mapping[str, Any]:
    selector = config["selector"]
    candidates: list[Mapping[str, Any]] = []
    seeds = sorted(records_by_seed_spec)
    for tie_width in map(float, config["proposal"]["near_tie_width_grid"]):
        for regret_budget in map(
            float, config["proposal"]["linear_regret_budget_grid"]
        ):
            spec = proposal_spec_key(tie_width, regret_budget)
            for benefit_threshold in map(
                float, selector["benefit_probability_threshold_grid"]
            ):
                for maximum_harm in map(
                    float, selector["maximum_harm_probability_grid"]
                ):
                    rows: list[tuple[Mapping[str, Any], bool]] = []
                    for seed in seeds:
                        predictions = oof_by_seed_spec[seed][spec]
                        for row in records_by_seed_spec[seed][spec]:
                            prediction = predictions[(seed, int(row["user_id"]))]
                            accepted = bool(
                                row["proposal_changed"]
                                and prediction["benefit_probability"]
                                >= benefit_threshold
                                and prediction["harm_probability"] <= maximum_harm
                            )
                            rows.append((row, accepted))
                    accepted_count = sum(accepted for _row, accepted in rows)
                    coverage = accepted_count / max(len(rows), 1)
                    pair_rows = [
                        (row, accepted)
                        for row, accepted in rows
                        if math.isfinite(float(row["preference_delta"]))
                    ]
                    accepted_pair = [row for row, accepted in pair_rows if accepted]
                    rows_by_user: dict[int, list[tuple[Mapping[str, Any], bool]]] = (
                        defaultdict(list)
                    )
                    for row, accepted in rows:
                        rows_by_user[int(row["user_id"])].append((row, accepted))
                    ndcg_delta = float(
                        np.mean(
                            [
                                np.mean(
                                    [
                                        float(row["ndcg_delta"]) if accepted else 0.0
                                        for row, accepted in user_rows
                                    ]
                                )
                                for user_rows in rows_by_user.values()
                            ]
                        )
                    )
                    preference_by_user: list[float] = []
                    for user_rows in rows_by_user.values():
                        finite_rows = [
                            (row, accepted)
                            for row, accepted in user_rows
                            if math.isfinite(float(row["preference_delta"]))
                        ]
                        if finite_rows:
                            preference_by_user.append(
                                float(
                                    np.mean(
                                        [
                                            float(row["preference_delta"])
                                            if accepted
                                            else 0.0
                                            for row, accepted in finite_rows
                                        ]
                                    )
                                )
                            )
                    preference_delta = (
                        float(np.mean(preference_by_user))
                        if preference_by_user
                        else float("nan")
                    )
                    conditional_preference = (
                        float(
                            np.mean(
                                [float(row["preference_delta"]) for row in accepted_pair]
                            )
                        )
                        if accepted_pair
                        else float("nan")
                    )
                    acceptance_by_user = [
                        float(np.mean([accepted for _row, accepted in user_rows]))
                        for user_rows in rows_by_user.values()
                    ]
                    harmful_acceptance_by_user = [
                        float(
                            np.mean(
                                [accepted and bool(row["harmful"]) for row, accepted in user_rows]
                            )
                        )
                        for user_rows in rows_by_user.values()
                    ]
                    harmful_rate = float(
                        sum(harmful_acceptance_by_user)
                        / max(sum(acceptance_by_user), 1e-12)
                    )
                    accepted_pair_user_count = len(
                        {
                            int(row["user_id"])
                            for row, accepted in pair_rows
                            if accepted
                        }
                    )
                    feasible = bool(
                        float(selector["minimum_validation_coverage"])
                        <= coverage
                        <= float(selector["maximum_validation_coverage"])
                        and accepted_count
                        >= int(selector["minimum_validation_accepted_requests"])
                        and accepted_pair_user_count
                        >= int(selector["minimum_validation_accepted_pair_users"])
                        and ndcg_delta
                        >= float(selector["minimum_validation_ndcg_delta"])
                        and math.isfinite(conditional_preference)
                        and conditional_preference > 0.0
                    )
                    coverage_penalty = max(
                        0.0,
                        float(selector["minimum_validation_coverage"]) - coverage,
                        coverage - float(selector["maximum_validation_coverage"]),
                    )
                    candidates.append(
                        {
                            "tie_width": tie_width,
                            "linear_regret_budget": regret_budget,
                            "benefit_probability_threshold": benefit_threshold,
                            "maximum_harm_probability": maximum_harm,
                            "coverage": coverage,
                            "validation_request_rows": len(rows),
                            "validation_accepted_request_rows": accepted_count,
                            "validation_accepted_pair_bearing_distinct_users": accepted_pair_user_count,
                            "policy_ndcg_delta": ndcg_delta,
                            "policy_preference_delta": preference_delta,
                            "accepted_conditional_preference_delta": conditional_preference,
                            "harmful_intervention_rate": harmful_rate,
                            "feasible": feasible,
                            "coverage_penalty": coverage_penalty,
                        }
                    )
    feasible_candidates = [row for row in candidates if row["feasible"]]
    if not feasible_candidates:
        raise IntegrityError(
            "No preregistered validation selector point is feasible; refusing to build T manifests"
        )
    pool = feasible_candidates
    selected = max(
        pool,
        key=lambda row: (
            float(row["policy_preference_delta"])
            if math.isfinite(float(row["policy_preference_delta"]))
            else -math.inf,
            -float(row["harmful_intervention_rate"]),
            float(row["policy_ndcg_delta"]),
            -float(row["coverage"]),
            -float(row["linear_regret_budget"]),
            -float(row["tie_width"]),
            -float(row["maximum_harm_probability"]),
            float(row["benefit_probability_threshold"]),
        ),
    )
    spec = proposal_spec_key(
        float(selected["tie_width"]), float(selected["linear_regret_budget"])
    )
    selected_rows = [
        (seed, row)
        for seed in seeds
        for row in records_by_seed_spec[seed][spec]
        if bool(row["proposal_changed"])
    ]
    control_count = int(selected["validation_accepted_request_rows"])
    if control_count <= 0 or control_count > len(selected_rows):
        raise IntegrityError("Matched-control V count is outside proposal-changed support")

    def control_hash(seed: int, user_id: int, method: str) -> str:
        return hashlib.sha256(
            f"{selector['deterministic_random_control_seed']}:{seed}:{user_id}".encode(
                "ascii"
            )
        ).hexdigest()

    near_keys = sorted(
        (
            float(row["near_tie_tightness"]),
            control_hash(seed, int(row["user_id"]), "near_tie_only"),
        )
        for seed, row in selected_rows
    )
    uncertainty_keys = sorted(
        (
            -float(row["uncertainty_score"]),
            control_hash(seed, int(row["user_id"]), "uncertainty_only"),
        )
        for seed, row in selected_rows
    )
    random_keys = sorted(
        (control_hash(seed, int(row["user_id"]), "random_matched"),)
        for seed, row in selected_rows
    )
    single_head_keys = sorted(
        (
            -float(
                oof_by_seed_spec[seed][spec][(seed, int(row["user_id"]))][
                    "single_head_probability"
                ]
            ),
            control_hash(seed, int(row["user_id"]), "single_head_selector_diagnostic"),
        )
        for seed, row in selected_rows
    )
    near_boundary = near_keys[control_count - 1]
    uncertainty_boundary = uncertainty_keys[control_count - 1]
    random_boundary = random_keys[control_count - 1]
    single_head_boundary = single_head_keys[control_count - 1]
    return {
        **dict(selected),
        "validation_selection_feasible": True,
        "candidate_grid_size": len(candidates),
        "validation_oof_harmful_intervention_rate": float(
            selected["harmful_intervention_rate"]
        ),
        "matched_control_validation_count": control_count,
        "near_tie_control_lexicographic_boundary": list(near_boundary),
        "uncertainty_control_lexicographic_boundary": list(uncertainty_boundary),
        "random_control_hash_boundary": random_boundary[0],
        "single_head_control_lexicographic_boundary": list(single_head_boundary),
        "matched_controls": (
            "exact K_V proposal-changed validation rows; boundaries freeze a "
            "descriptor-plus-request-hash lexicographic predicate for T"
        ),
        "selection_order": (
            "maximize_oof_preference_uplift_then_minimize_harm_then_maximize_ndcg_"
            "then_minimize_coverage_with_deterministic_grid_ties"
        ),
        "test_outcomes_used": False,
    }


def control_request_hash(
    user_id: int, seed: int, method: str, selector: Mapping[str, Any]
) -> str:
    return hashlib.sha256(
        f"{selector['deterministic_random_control_seed']}:{seed}:{user_id}".encode(
            "ascii"
        )
    ).hexdigest()


def _policy_output(
    linear: LinearDefault, proposal: Proposal, accepted: bool
) -> PolicyOutput:
    if accepted and proposal.changed:
        return PolicyOutput(
            ranking=proposal.ranking,
            scores=proposal.scores,
            accepted=True,
            exact_fallback=False,
        )
    output = PolicyOutput(
        ranking=linear.ranking,
        scores=linear.scores,
        accepted=False,
        exact_fallback=True,
    )
    if (
        output.ranking != linear.ranking
        or output.scores.tobytes(order="C") != linear.scores.tobytes(order="C")
    ):
        raise IntegrityError("Rejected request is not an exact linear fallback")
    return output


def _always_on_policy_output(proposal: Proposal) -> PolicyOutput:
    """Serve the exact registered finite proposal with no selector decision."""
    return PolicyOutput(
        ranking=proposal.ranking,
        scores=proposal.scores,
        accepted=True,
        exact_fallback=False,
    )


def _score_bits(
    items: Sequence[int], ranking: Sequence[int], scores: np.ndarray, k: int = 10
) -> list[str]:
    index = {int(item): position for position, item in enumerate(items)}
    return [
        np.asarray(scores[index[int(item)]], dtype=np.float32).tobytes().hex()
        for item in ranking[:k]
    ]


def canonical_top10_record(
    items: Sequence[int], ranking: Sequence[int], scores: np.ndarray
) -> bytes:
    index = {int(item): position for position, item in enumerate(items)}
    item_bytes = np.asarray(ranking[:10], dtype="<i4").tobytes(order="C")
    score_bytes = np.asarray(
        [scores[index[int(item)]] for item in ranking[:10]], dtype="<f4"
    ).tobytes(order="C")
    return item_bytes + score_bytes


def canonical_full_union_record(
    items: Sequence[int], ranking: Sequence[int], scores: np.ndarray
) -> bytes:
    """Canonical full-order record used by the exact-fallback audit."""
    if len(ranking) != len(items) or set(map(int, ranking)) != set(map(int, items)):
        raise IntegrityError("Canonical full-union record is not a permutation")
    index = {int(item): position for position, item in enumerate(items)}
    item_bytes = np.asarray(ranking, dtype="<i4").tobytes(order="C")
    score_bytes = np.asarray(
        [scores[index[int(item)]] for item in ranking], dtype="<f4"
    ).tobytes(order="C")
    return item_bytes + score_bytes


def _float32_array_evidence(values: np.ndarray) -> Mapping[str, Any]:
    """Persist an exact, portable query record rather than a rounded JSON list."""
    array = np.ascontiguousarray(np.asarray(values, dtype="<f4"))
    payload = array.tobytes(order="C")
    return {
        "dtype": "little-endian-float32",
        "shape": list(array.shape),
        "bytes_hex": payload.hex(),
        "sha256": core.sha256_bytes(payload),
    }


def candidate_context_provenance(
    context: CandidateContext,
    history: Sequence[Interaction],
    collaborative_index_sha256: str,
    semantic_index_sha256: str,
    additional_queries: Mapping[str, np.ndarray] | None = None,
) -> Mapping[str, Any]:
    """Return the complete target-blind candidate/query provenance record."""
    seen = sorted({int(event.item_index) for event in history})
    union = tuple(int(item) for item in context.union)
    query_records: dict[str, Mapping[str, Any]] = {
        "collaborative": _float32_array_evidence(context.collaborative_query),
        "semantic": _float32_array_evidence(context.semantic_query),
        "dislike": _float32_array_evidence(context.dislike_query),
    }
    for name, values in sorted((additional_queries or {}).items()):
        query_records[str(name)] = _float32_array_evidence(values)
    prefix_rows = [
        [
            int(event.user_id),
            int(event.item_index),
            int(event.rating),
            int(event.timestamp),
            int(event.ordinal),
        ]
        for event in history
    ]
    candidate_set = set(context.collaborative) | set(context.semantic)
    return {
        "query_records": query_records,
        "branch_rank_by_union_position": {
            "collaborative": [
                int(context.collaborative_rank.get(item, -1)) for item in union
            ],
            "semantic": [int(context.semantic_rank.get(item, -1)) for item in union],
        },
        "branch_membership_by_union_position": {
            "collaborative": [item in context.collaborative_rank for item in union],
            "semantic": [item in context.semantic_rank for item in union],
        },
        "seen_filter": {
            "seen_item_indices": seen,
            "candidate_seen_overlap_count": len(candidate_set & set(seen)),
            "all_candidates_unseen": not bool(candidate_set & set(seen)),
            "prefix_rows_sha256": core.sha256_bytes(
                core.canonical_json_bytes(prefix_rows)
            ),
        },
        "index_sha256": {
            "collaborative_memory": str(collaborative_index_sha256),
            "semantic_memory": str(semantic_index_sha256),
        },
        "target_blind_context_features": {
            "history_log_feature": float(context.history_log_feature),
            "bpr_q05": float(context.bpr_min),
            "bpr_q95_minus_q05": float(context.bpr_span),
            "semantic_q05": float(context.semantic_min),
            "semantic_q95_minus_q05": float(context.semantic_span),
            "regret_scale_degenerate": bool(context.regret_scale_degenerate),
        },
    }


def build_test_policy_manifest(
    splits: Sequence[UserSplit],
    candidate_manifest: Mapping[int, CandidateManifestEntry],
    bpr: BPRArtifacts,
    semantic_vectors: np.ndarray,
    popularity: np.ndarray,
    residual_model: BoundedResidual,
    router: RouterBundle,
    linear_alpha: float,
    selection: Mapping[str, Any],
    seed: int,
    config: Mapping[str, Any],
) -> tuple[Mapping[int, TestPolicyEntry], list[Mapping[str, Any]]]:
    """Construct all target-blind decisions and outputs before reading T."""
    result: dict[int, TestPolicyEntry] = {}
    serializable: list[Mapping[str, Any]] = []
    for split in splits:
        candidates = candidate_manifest[split.user_id]
        context = candidates.context
        linear = materialize_linear_default(
            context, bpr, semantic_vectors, popularity, linear_alpha, config
        )
        residual = core.residual_numpy(residual_model, linear.features)
        proposal = make_proposal(
            linear,
            residual,
            float(selection["tie_width"]),
            float(selection["linear_regret_budget"]),
            config,
        )
        # The always-on comparator serves this exact same selected finite
        # proposal on every request; only the selector decision is removed.
        always_on_proposal = proposal
        descriptor = proposal.descriptor.reshape(1, -1)
        benefit_probability = float(router.benefit.predict(descriptor)[0])
        harm_probability = float(router.harm.predict(descriptor)[0])
        single_head_probability = float(router.single_head.predict(descriptor)[0])
        decisions = {
            "linear": False,
            "always_on": True,
            "near_tie_only": bool(
                proposal.changed
                and (
                    proposal.near_tie_tightness,
                    control_request_hash(
                        split.user_id, seed, "near_tie_only", config["selector"]
                    ),
                )
                <= tuple(selection["near_tie_control_lexicographic_boundary"])
            ),
            "uncertainty_only": bool(
                proposal.changed
                and (
                    -proposal.uncertainty_score,
                    control_request_hash(
                        split.user_id, seed, "uncertainty_only", config["selector"]
                    ),
                )
                <= tuple(selection["uncertainty_control_lexicographic_boundary"])
            ),
            "random_matched": bool(
                proposal.changed
                and control_request_hash(
                    split.user_id, seed, "random_matched", config["selector"]
                )
                <= str(selection["random_control_hash_boundary"])
            ),
            "single_head_selector_diagnostic": bool(
                proposal.changed
                and (
                    -single_head_probability,
                    control_request_hash(
                        split.user_id,
                        seed,
                        "single_head_selector_diagnostic",
                        config["selector"],
                    ),
                )
                <= tuple(selection["single_head_control_lexicographic_boundary"])
            ),
            "ravel": bool(
                proposal.changed
                and benefit_probability
                >= float(selection["benefit_probability_threshold"])
                and harm_probability <= float(selection["maximum_harm_probability"])
            ),
        }
        outputs = {}
        for method, accepted in decisions.items():
            method_proposal = always_on_proposal if method == "always_on" else proposal
            if method == "always_on":
                # This registered control serves the same selected finite
                # proposal on every request, including a no-op proposal.
                outputs[method] = _always_on_policy_output(method_proposal)
            else:
                outputs[method] = _policy_output(linear, method_proposal, accepted)
        probabilities = {
            "benefit_probability": benefit_probability,
            "harm_probability": harm_probability,
            "single_head_probability": single_head_probability,
        }
        entry = TestPolicyEntry(
            candidates,
            linear,
            proposal,
            always_on_proposal,
            outputs,
            probabilities,
        )
        result[split.user_id] = entry
        linear_canonical = canonical_top10_record(
            linear.items, linear.ranking, linear.scores
        )
        linear_full_canonical = canonical_full_union_record(
            linear.items, linear.ranking, linear.scores
        )
        serializable.append(
            {
                "user_id": split.user_id,
                "history_event_count": len(
                    (*split.train, *split.alignment, *split.validation)
                ),
                "selected_bpr_candidates_B": list(context.collaborative),
                "semantic_candidates_S": list(context.semantic),
                "union_candidates_C": list(context.union),
                "B_subset_C": set(context.collaborative).issubset(context.union),
                "target_labels_joined": False,
                "linear_top10": list(linear.ranking[:10]),
                "linear_top10_score_bits": _score_bits(
                    linear.items, linear.ranking, linear.scores
                ),
                "linear_canonical_top10_record_hex": linear_canonical.hex(),
                "linear_canonical_top10_record_sha256": core.sha256_bytes(
                    linear_canonical
                ),
                "linear_canonical_full_union_record_hex": linear_full_canonical.hex(),
                "linear_canonical_full_union_record_sha256": core.sha256_bytes(
                    linear_full_canonical
                ),
                "linear_full_union_ranking": list(linear.ranking),
                "linear_union_score_bits_by_union_item": [
                    np.asarray(value, dtype=np.float32).tobytes().hex()
                    for value in linear.scores
                ],
                "proposal_top10": list(proposal.ranking[:10]),
                "proposal_top10_score_bits": _score_bits(
                    linear.items, proposal.ranking, proposal.scores
                ),
                "proposal_full_union_ranking": list(proposal.ranking),
                "proposal_union_score_bits_by_union_item": [
                    np.asarray(value, dtype=np.float32).tobytes().hex()
                    for value in proposal.scores
                ],
                "selected_bpr_full_union_ranking": core.rank_descending(
                    context.union, linear.bpr_scores
                ),
                "selected_bpr_union_score_bits_by_union_item": [
                    np.asarray(value, dtype=np.float32).tobytes().hex()
                    for value in linear.bpr_scores
                ],
                "proposal_changed": proposal.changed,
                "proposal_linear_regret": proposal.linear_regret,
                "proposal_fail_closed_reason": proposal.fail_closed_reason,
                "always_on_uses_same_selected_finite_proposal": True,
                "always_on_top10": list(always_on_proposal.ranking[:10]),
                "always_on_full_union_ranking": list(always_on_proposal.ranking),
                "always_on_union_score_bits_by_union_item": [
                    np.asarray(value, dtype=np.float32).tobytes().hex()
                    for value in always_on_proposal.scores
                ],
                "selector_descriptor": proposal.descriptor.tolist(),
                "selector_probabilities": probabilities,
                "decisions": decisions,
                "outputs": {
                    method: {
                        "top10": list(output.ranking[:10]),
                        "top10_score_bits": _score_bits(
                            linear.items, output.ranking, output.scores
                        ),
                        "full_union_ranking": list(output.ranking),
                        "union_score_bits_by_union_item": [
                            np.asarray(value, dtype="<f4").tobytes().hex()
                            for value in output.scores
                        ],
                        "accepted": output.accepted,
                        "exact_fallback": output.exact_fallback,
                        "canonical_top10_record_hex": canonical_top10_record(
                            linear.items, output.ranking, output.scores
                        ).hex(),
                        "canonical_top10_record_sha256": core.sha256_bytes(
                            canonical_top10_record(
                                linear.items, output.ranking, output.scores
                            )
                        ),
                        "canonical_full_union_record_hex": canonical_full_union_record(
                            linear.items, output.ranking, output.scores
                        ).hex(),
                        "canonical_full_union_record_sha256": core.sha256_bytes(
                            canonical_full_union_record(
                                linear.items, output.ranking, output.scores
                            )
                        ),
                    }
                    for method, output in outputs.items()
                },
                "all_choices_frozen_before_test_manifest": True,
            }
        )
    if set(result) != {split.user_id for split in splits}:
        raise IntegrityError("Test policy manifest does not cover the RAVEL cohort")
    return result, serializable


METHODS = (
    "selected_bpr",
    "linear",
    "always_on",
    "near_tie_only",
    "uncertainty_only",
    "random_matched",
    "single_head_selector_diagnostic",
    "ravel",
)


def evaluate_test_seed(
    splits: Sequence[UserSplit],
    manifest: Mapping[int, TestPolicyEntry],
    config: Mapping[str, Any],
    catalog_item_ids: Sequence[int],
) -> tuple[Mapping[str, list[Mapping[str, Any]]], Mapping[str, Any]]:
    """The only function permitted to join sealed T ratings to outputs."""
    rows: dict[str, list[Mapping[str, Any]]] = {method: [] for method in METHODS}
    heldout_pairs = 0
    pair_users = 0
    exact_fallback = True
    support = True
    candidate_recall = True
    maximum_regret = 0.0
    for split in splits:
        entry = manifest[split.user_id]
        context = entry.candidates.context
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
        pairs, raw_pairs = preference_pairs_by_movie_id(
            [event for event in split.test if event.item_index in context.union],
            int(config["dataset"]["preference_pair_minimum_rating_gap"]),
            int(config["evaluation"]["maximum_preference_pairs_per_user"]),
            int(config["evaluation"]["preference_pair_subsample_seed"]),
            split.user_id,
            catalog_item_ids,
        )
        heldout_pairs += len(pairs)
        pair_users += int(bool(pairs))
        union_recall = core.recall_at_k(context.union, targets, len(context.union))
        branch_recall = core.recall_at_k(
            context.collaborative, targets, len(context.collaborative)
        )
        support = support and set(context.collaborative).issubset(context.union)
        candidate_recall = candidate_recall and union_recall + 1e-12 >= branch_recall
        maximum_regret = max(maximum_regret, entry.proposal.linear_regret)
        for method in METHODS:
            if method == "selected_bpr":
                ranking = context.collaborative
                scores = entry.linear.bpr_scores
                pair_ranking = core.rank_descending(context.union, scores)
                accepted = False
                fallback = True
                candidate_metric = branch_recall
            else:
                output = entry.outputs[method]
                ranking = output.ranking
                scores = output.scores
                pair_ranking = output.ranking
                accepted = output.accepted
                fallback = output.exact_fallback
                candidate_metric = union_recall
            accuracy, correct = _pair_accuracy(pairs, pair_ranking)
            exact_fallback = exact_fallback and (
                accepted
                or (
                    tuple(ranking) == tuple(entry.linear.ranking)
                    and scores.tobytes(order="C")
                    == entry.linear.scores.tobytes(order="C")
                    and canonical_full_union_record(
                        entry.linear.items, ranking, scores
                    )
                    == canonical_full_union_record(
                        entry.linear.items,
                        entry.linear.ranking,
                        entry.linear.scores,
                    )
                    and core.sha256_bytes(
                        canonical_full_union_record(
                            entry.linear.items, ranking, scores
                        )
                    )
                    == core.sha256_bytes(
                        canonical_full_union_record(
                            entry.linear.items,
                            entry.linear.ranking,
                            entry.linear.scores,
                        )
                    )
                    and fallback
                )
                or method == "selected_bpr"
            )
            rows[method].append(
                {
                    "user_id": split.user_id,
                    "ndcg_at_10": core.binary_ndcg(
                        ranking, targets, int(config["evaluation"]["ndcg_k"])
                    ),
                    "recall_at_10": core.recall_at_k(
                        ranking, targets, int(config["evaluation"]["recall_k"])
                    ),
                    "preference_pair_accuracy": accuracy,
                    "preference_pairs": len(pairs),
                    "preference_correct": correct,
                    "raw_natural_preference_pairs_before_cap": raw_pairs,
                    "future_dislike_intrusion_at_10": float(
                        len(set(ranking[:10]) & set(dislikes)) / 10.0
                    ),
                    "candidate_recall": candidate_metric,
                    "union_candidate_recall_at_most_400": union_recall,
                    "collaborative_candidate_recall_at_200": branch_recall,
                    "candidate_support_inclusion": set(context.collaborative).issubset(
                        context.union
                    ),
                    "accepted": float(accepted),
                    "exact_fallback": bool(fallback),
                }
            )
        linear_row = rows["linear"][-1]
        for method in METHODS:
            row = rows[method][-1]
            row["ndcg_delta_vs_linear"] = float(row["ndcg_at_10"]) - float(
                linear_row["ndcg_at_10"]
            )
            row["preference_delta_vs_linear"] = (
                float(row["preference_pair_accuracy"])
                - float(linear_row["preference_pair_accuracy"])
                if math.isfinite(float(row["preference_pair_accuracy"]))
                and math.isfinite(float(linear_row["preference_pair_accuracy"]))
                else float("nan")
            )
            row["harmful_intervention"] = bool(
                float(row["accepted"]) > 0.0
                and float(row["ndcg_delta_vs_linear"]) < 0.0
            )
    ravel_rows = rows["ravel"]
    accepted = [row for row in ravel_rows if float(row["accepted"]) > 0.0]
    accepted_pair = [
        row
        for row in accepted
        if math.isfinite(float(row["preference_delta_vs_linear"]))
    ]
    return rows, {
        "heldout_preference_pairs": heldout_pairs,
        "pair_bearing_test_users": pair_users,
        "accepted_requests": len(accepted),
        "accepted_pair_bearing_requests": len(accepted_pair),
        "accepted_conditional_preference_uplift": (
            float(np.mean([row["preference_delta_vs_linear"] for row in accepted_pair]))
            if accepted_pair
            else None
        ),
        "harmful_intervention_rate": (
            float(np.mean([row["harmful_intervention"] for row in accepted]))
            if accepted
            else None
        ),
        "candidate_support_inclusion_all_requests": support,
        "union_candidate_recall_never_below_collaborative": candidate_recall,
        "exact_fallback_all_rejected_requests": exact_fallback,
        "maximum_linear_anchor_regret": maximum_regret,
        "candidate_targets_injected": False,
    }


NUMERIC_METRICS = (
    "ndcg_at_10",
    "recall_at_10",
    "preference_pair_accuracy",
    "future_dislike_intrusion_at_10",
    "candidate_recall",
    "union_candidate_recall_at_most_400",
    "collaborative_candidate_recall_at_200",
    "accepted",
    "harmful_intervention",
    "ndcg_delta_vs_linear",
    "preference_delta_vs_linear",
)


def summarize_rows(rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    summary: dict[str, Any] = {"users": len(rows)}
    for metric in NUMERIC_METRICS:
        values = np.asarray([float(row[metric]) for row in rows], dtype=np.float64)
        finite = values[np.isfinite(values)]
        summary[metric] = float(np.mean(finite)) if len(finite) else None
        summary[f"{metric}_cohort_users"] = len(finite)
    pair_count = float(sum(float(row["preference_pairs"]) for row in rows))
    correct = float(sum(float(row["preference_correct"]) for row in rows))
    summary["preference_pairs"] = pair_count
    summary["preference_pair_accuracy_pair_micro_diagnostic"] = (
        correct / pair_count if pair_count else None
    )
    summary["candidate_support_inclusion_all"] = all(
        bool(row["candidate_support_inclusion"]) for row in rows
    )
    summary["exact_fallback_all_rejections"] = all(
        float(row["accepted"]) > 0.0 or bool(row["exact_fallback"]) for row in rows
    )
    return summary


def average_method_rows(
    per_seed_rows: Mapping[int, Mapping[str, list[Mapping[str, Any]]]], method: str
) -> list[Mapping[str, Any]]:
    by_user: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for methods in per_seed_rows.values():
        for row in methods[method]:
            by_user[int(row["user_id"])].append(row)
    averaged: list[Mapping[str, Any]] = []
    for user_id in sorted(by_user):
        source = by_user[user_id]
        row: dict[str, Any] = {"user_id": user_id}
        for metric in NUMERIC_METRICS:
            values = np.asarray([float(item[metric]) for item in source], dtype=np.float64)
            finite = values[np.isfinite(values)]
            row[metric] = float(np.mean(finite)) if len(finite) else float("nan")
        row["preference_pairs"] = float(
            np.mean([float(item["preference_pairs"]) for item in source])
        )
        row["preference_correct"] = float(
            np.mean([float(item["preference_correct"]) for item in source])
        )
        row["candidate_support_inclusion"] = all(
            bool(item["candidate_support_inclusion"]) for item in source
        )
        row["exact_fallback"] = all(
            float(item["accepted"]) > 0.0 or bool(item["exact_fallback"])
            for item in source
        )
        averaged.append(row)
    return averaged


def accepted_pair_bearing_support(
    per_seed_rows: Mapping[int, Mapping[str, list[Mapping[str, Any]]]],
) -> float:
    """Seed-averaged count of rows where acceptance and pair support coincide."""
    seeds = sorted(per_seed_rows)
    if not seeds:
        raise IntegrityError("Accepted pair-bearing support has no seeds")
    user_sets = [
        {int(row["user_id"]) for row in per_seed_rows[seed]["ravel"]}
        for seed in seeds
    ]
    if any(users != user_sets[0] for users in user_sets[1:]):
        raise IntegrityError("Accepted pair-bearing support cohorts differ by seed")
    return float(
        sum(
            float(row["accepted"])
            for seed in seeds
            for row in per_seed_rows[seed]["ravel"]
            if math.isfinite(float(row["preference_pair_accuracy"]))
        )
        / len(seeds)
    )


def benchmark_latency(
    splits: Sequence[UserSplit],
    bpr: BPRArtifacts,
    collaborative_index: Any,
    semantic_vectors: np.ndarray,
    semantic_index: Any,
    popularity: np.ndarray,
    residual_model: BoundedResidual,
    router: RouterBundle,
    linear_alpha: float,
    selection: Mapping[str, Any],
    config: Mapping[str, Any],
) -> Mapping[str, Any]:
    measured_count = min(
        len(splits), int(config["evaluation"]["latency_measured_users"])
    )
    warmup_count = min(
        measured_count, int(config["evaluation"]["latency_warmup_users"])
    )
    measured = list(splits[:measured_count])

    def run_one(split: UserSplit, method: str) -> None:
        history = (*split.train, *split.alignment, *split.validation)
        context = core.build_candidate_context(
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
        linear = materialize_linear_default(
            context, bpr, semantic_vectors, popularity, linear_alpha, config
        )
        if method == "ravel":
            residual = core.residual_numpy(residual_model, linear.features)
            proposal = make_proposal(
                linear,
                residual,
                float(selection["tie_width"]),
                float(selection["linear_regret_budget"]),
                config,
            )
            descriptor = proposal.descriptor.reshape(1, -1)
            accepted = bool(
                proposal.changed
                and float(router.benefit.predict(descriptor)[0])
                >= float(selection["benefit_probability_threshold"])
                and float(router.harm.predict(descriptor)[0])
                <= float(selection["maximum_harm_probability"])
            )
            _policy_output(linear, proposal, accepted)

    for split in measured[:warmup_count]:
        run_one(split, "linear")
        run_one(split, "ravel")
    timings: dict[str, list[list[float]]] = {
        "linear": [[] for _ in measured],
        "ravel": [[] for _ in measured],
    }
    repetitions = int(config["evaluation"]["latency_repetitions"])
    for repetition in range(repetitions):
        for position, split in enumerate(measured):
            order = (
                ("linear", "ravel")
                if (repetition + position) % 2 == 0
                else ("ravel", "linear")
            )
            for method in order:
                started = time.perf_counter_ns()
                run_one(split, method)
                timings[method][position].append(
                    (time.perf_counter_ns() - started) / 1_000_000.0
                )
    output: dict[str, Any] = {
        "single_thread_cpu": True,
        "includes_both_searches_union_features_default_residual_proposal_selector_sort": True,
        "measured_users": measured_count,
        "repetitions": repetitions,
        "abba_interleaving": True,
    }
    for method, values_by_user in timings.items():
        medians = np.asarray(
            [float(np.median(values)) for values in values_by_user], dtype=np.float64
        )
        output[method] = {
            "p50_ms": float(np.percentile(medians, 50.0)),
            "p95_ms": float(np.percentile(medians, 95.0)),
            "mean_of_user_medians_ms": float(np.mean(medians)),
            "per_user_median_ms": medians.tolist(),
            "aggregation": (
                "median_across_repetitions_per_user_then_percentile_across_users"
            ),
        }
    output["ravel_to_linear_p95_ratio"] = float(
        output["ravel"]["p95_ms"] / max(output["linear"]["p95_ms"], 1e-12)
    )
    return output


def evaluate_ten_part_gate(
    per_seed_rows: Mapping[int, Mapping[str, list[Mapping[str, Any]]]],
    per_seed_diagnostics: Mapping[int, Mapping[str, Any]],
    latency_by_seed: Mapping[int, Mapping[str, Any]],
    selection: Mapping[str, Any],
    integrity: Mapping[str, Any],
    config: Mapping[str, Any],
) -> Mapping[str, Any]:
    seeds = sorted(per_seed_rows)
    averaged = {method: average_method_rows(per_seed_rows, method) for method in METHODS}
    summaries = {method: summarize_rows(rows) for method, rows in averaged.items()}
    repetitions = int(config["evaluation"]["bootstrap_repetitions"])
    alpha = float(config["evaluation"]["bootstrap_alpha"])
    bootstrap_seed = int(config["evaluation"]["bootstrap_seed"])

    def bootstrap(proposed: str, baseline: str, metric: str, offset: int) -> Mapping[str, Any]:
        return core.paired_user_cluster_bootstrap(
            averaged[proposed],
            averaged[baseline],
            metric,
            repetitions,
            alpha,
            bootstrap_seed + offset,
        )

    bootstraps = {
        "linear_minus_bpr_ndcg": bootstrap("linear", "selected_bpr", "ndcg_at_10", 0),
        "ravel_minus_linear_ndcg": bootstrap("ravel", "linear", "ndcg_at_10", 1),
        "ravel_minus_linear_preference": bootstrap(
            "ravel", "linear", "preference_pair_accuracy", 2
        ),
        "ravel_minus_linear_recall": bootstrap("ravel", "linear", "recall_at_10", 3),
        "ravel_minus_linear_dislike": bootstrap(
            "ravel", "linear", "future_dislike_intrusion_at_10", 4
        ),
    }
    gate = config["promise_gate"]
    linear_ndcg = summaries["linear"]["ndcg_at_10"]
    bpr_ndcg = summaries["selected_bpr"]["ndcg_at_10"]
    relative_linear_gain = (
        None
        if linear_ndcg is None or bpr_ndcg is None or float(bpr_ndcg) <= 0.0
        else (float(linear_ndcg) - float(bpr_ndcg)) / float(bpr_ndcg)
    )
    g1 = bool(
        relative_linear_gain is not None
        and relative_linear_gain >= float(gate["minimum_linear_relative_ndcg_gain_over_bpr"])
        and bootstraps["linear_minus_bpr_ndcg"]["lower"] is not None
        and float(bootstraps["linear_minus_bpr_ndcg"]["lower"]) > 0.0
    )
    ndcg_difference = bootstraps["ravel_minus_linear_ndcg"]
    g2 = bool(
        ndcg_difference["mean_difference"] is not None
        and float(ndcg_difference["mean_difference"])
        >= float(gate["minimum_ravel_minus_linear_ndcg_point"])
        and ndcg_difference["lower"] is not None
        and float(ndcg_difference["lower"])
        > float(gate["minimum_ravel_minus_linear_ndcg_lower"])
    )
    preference_difference = bootstraps["ravel_minus_linear_preference"]
    g3 = bool(
        preference_difference["mean_difference"] is not None
        and float(preference_difference["mean_difference"])
        >= float(gate["minimum_absolute_preference_accuracy_gain"])
        and preference_difference["lower"] is not None
        and float(preference_difference["lower"]) > 0.0
    )
    heuristic_methods = ("near_tie_only", "uncertainty_only", "random_matched")
    accepted_pair_rows = [
        row
        for seed in seeds
        for row in per_seed_rows[seed]["ravel"]
        if float(row["accepted"]) > 0.0
        and math.isfinite(float(row["preference_delta_vs_linear"]))
    ]
    conditional_uplift = (
        float(
            sum(float(row["preference_delta_vs_linear"]) for row in accepted_pair_rows)
            / len(accepted_pair_rows)
        )
        if accepted_pair_rows
        else None
    )
    g4 = bool(
        summaries["ravel"]["ndcg_at_10"] is not None
        and summaries["always_on"]["ndcg_at_10"] is not None
        and float(summaries["ravel"]["ndcg_at_10"])
        > float(summaries["always_on"]["ndcg_at_10"])
        and all(
            summaries["ravel"]["preference_pair_accuracy"] is not None
            and summaries[method]["preference_pair_accuracy"] is not None
            and float(summaries["ravel"]["preference_pair_accuracy"])
            > float(summaries[method]["preference_pair_accuracy"])
            for method in heuristic_methods
        )
        and conditional_uplift is not None
        and conditional_uplift > 0.0
    )
    ravel_rows = averaged["ravel"]
    coverage = float(np.mean([float(row["accepted"]) for row in ravel_rows]))
    accepted_requests = float(sum(float(row["accepted"]) for row in ravel_rows))
    accepted_pair_requests = accepted_pair_bearing_support(per_seed_rows)
    harmful_numerator = sum(
        float(row["harmful_intervention"]) for row in ravel_rows
    )
    harmful_rate = harmful_numerator / max(accepted_requests, 1e-12)
    harm_transfer_gap = harmful_rate - float(
        selection["validation_oof_harmful_intervention_rate"]
    )
    g5 = bool(
        bool(selection["validation_selection_feasible"])
        and float(gate["minimum_coverage"]) <= coverage <= float(gate["maximum_coverage"])
        and accepted_requests >= int(gate["minimum_accepted_test_requests"])
        and accepted_pair_requests
        >= int(gate["minimum_accepted_pair_bearing_test_requests"])
        and harm_transfer_gap <= float(gate["maximum_harm_rate_transfer_gap"])
    )
    g6 = bool(
        bootstraps["ravel_minus_linear_recall"]["lower"] is not None
        and float(bootstraps["ravel_minus_linear_recall"]["lower"])
        > float(gate["minimum_recall10_lower_bound"])
        and bootstraps["ravel_minus_linear_dislike"]["upper"] is not None
        and float(bootstraps["ravel_minus_linear_dislike"]["upper"])
        <= float(gate["maximum_absolute_dislike_intrusion_increase"])
    )
    g7_checks = {
        "B_subset_C_all_requests": all(
            bool(value["candidate_support_inclusion_all_requests"])
            for value in per_seed_diagnostics.values()
        ),
        "union_candidate_recall_never_below_collaborative": all(
            bool(value["union_candidate_recall_never_below_collaborative"])
            for value in per_seed_diagnostics.values()
        ),
        "exact_fallback_all_rejected_requests": all(
            bool(value["exact_fallback_all_rejected_requests"])
            for value in per_seed_diagnostics.values()
        ),
    }
    g7 = all(g7_checks.values())
    stable: dict[str, bool] = {}
    for seed in seeds:
        ravel_summary = summarize_rows(per_seed_rows[seed]["ravel"])
        linear_summary = summarize_rows(per_seed_rows[seed]["linear"])
        ndcg_delta = float(ravel_summary["ndcg_at_10"] - linear_summary["ndcg_at_10"])
        preference_delta = float(
            ravel_summary["preference_pair_accuracy"]
            - linear_summary["preference_pair_accuracy"]
        )
        stable[str(seed)] = bool(
            ndcg_delta >= float(gate["minimum_ravel_minus_linear_ndcg_point"])
            and preference_delta > 0.0
        )
    g8 = sum(stable.values()) >= int(gate["minimum_stable_seeds"])
    worst_p95 = max(float(value["ravel"]["p95_ms"]) for value in latency_by_seed.values())
    worst_ratio = max(
        float(value["ravel_to_linear_p95_ratio"]) for value in latency_by_seed.values()
    )
    g9 = bool(
        worst_p95 <= float(gate["maximum_p95_latency_ms"])
        and worst_ratio <= float(gate["maximum_p95_latency_ratio_to_linear"])
    )
    cohort_floors = all(
        int(value["heldout_preference_pairs"])
        >= int(config["dataset"]["minimum_heldout_preference_pairs"])
        and int(value["pair_bearing_test_users"])
        >= int(config["dataset"]["minimum_pair_bearing_test_users"])
        for value in per_seed_diagnostics.values()
    )
    g10_checks = {
        "test_preference_cohort_floors": cohort_floors,
        "prospective_cohorts_disjoint": bool(integrity.get("cohort_disjointness")),
        "immutable_matrices_and_indexes": bool(integrity.get("immutable")),
        "all_target_blind_manifests_stable": bool(integrity.get("manifests_stable")),
        "target_injection_count_zero": all(
            not bool(value["candidate_targets_injected"])
            for value in per_seed_diagnostics.values()
        ),
        "temporal_and_provenance": bool(integrity.get("temporal_and_provenance")),
        "source_config_and_dependency_hashes_stable": bool(
            integrity.get("source_hashes_stable")
        ),
        "asynchronous_error_ledger_empty": bool(integrity.get("async_ledger_empty")),
        "runner_completion_candidate_and_external_post_exit_verification_required": True,
    }
    g10 = all(g10_checks.values())
    gates = {
        "G1_strong_default_relevance": {
            "passed": g1,
            "relative_linear_ndcg_gain_over_bpr": relative_linear_gain,
            "bootstrap": bootstraps["linear_minus_bpr_ndcg"],
        },
        "G2_primary_relevance_noninferiority": {
            "passed": g2,
            "bootstrap": ndcg_difference,
        },
        "G3_primary_preference_gain": {
            "passed": g3,
            "bootstrap": preference_difference,
            "measurement": (
                "final constrained full order with frozen-linear nonselected tail"
            ),
        },
        "G4_selective_mechanism": {
            "passed": g4,
            "accepted_conditional_preference_uplift": conditional_uplift,
            "heuristic_controls": list(heuristic_methods),
        },
        "G5_nontrivial_calibrated_coverage": {
            "passed": g5,
            "test_coverage": coverage,
            "accepted_requests_seed_averaged": accepted_requests,
            "accepted_pair_requests_seed_averaged": accepted_pair_requests,
            "accepted_pair_support_formula": (
                "sum_u mean_s[accepted(u,s) * 1(preference_pairs(u,s)>0)]"
            ),
            "test_harmful_intervention_rate": harmful_rate,
            "validation_oof_harmful_intervention_rate": selection[
                "validation_oof_harmful_intervention_rate"
            ],
            "harm_rate_transfer_gap": harm_transfer_gap,
        },
        "G6_top_rank_and_exposure_safety": {
            "passed": g6,
            "recall_bootstrap": bootstraps["ravel_minus_linear_recall"],
            "dislike_bootstrap": bootstraps["ravel_minus_linear_dislike"],
        },
        "G7_candidate_support_and_exact_fallback": {
            "passed": g7,
            "checks": g7_checks,
        },
        "G8_seed_stability": {"passed": g8, "seed_checks": stable},
        "G9_serving_budget": {
            "passed": g9,
            "worst_ravel_p95_ms": worst_p95,
            "worst_ratio_to_linear": worst_ratio,
        },
        "G10_integrity": {
            "passed": g10,
            "checks": g10_checks,
            "external_process_exit_lock_release_and_recursive_hash_closure_pending": True,
        },
    }
    return {
        "passed": all(bool(value["passed"]) for value in gates.values()),
        "formula": "PROMISING = G1 & G2 & G3 & G4 & G5 & G6 & G7 & G8 & G9 & G10",
        "gates": gates,
        "seed_averaged_method_summaries": summaries,
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
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for seed in sorted(per_seed_rows):
        for method in METHODS:
            for row in per_seed_rows[seed][method]:
                writer.writerow(
                    {
                        "seed": seed,
                        "method": method,
                        **{field: row[field] for field in fields[2:]},
                    }
                )
    return buffer.getvalue().encode("utf-8")


def execute(args: argparse.Namespace) -> Path:
    config_path = args.config.resolve()
    protocol_path = args.protocol.resolve()
    experiments_root = args.output_root.resolve()
    if not config_path.is_file():
        raise FileNotFoundError(config_path)
    if not protocol_path.is_file():
        raise FileNotFoundError(protocol_path)
    config_bytes = config_path.read_bytes()
    config = json.loads(config_bytes.decode("utf-8"))
    validate_config(config)
    runner_path = Path(__file__).resolve()
    core_path = Path(core.__file__).resolve()
    project_root = runner_path.parents[1]
    question_path = project_root / "research-question-cycle3.md"
    survey_path = project_root / "literature" / "cycle3-survey-and-ideation.md"
    for required in (question_path, survey_path):
        if not required.is_file():
            raise FileNotFoundError(required)
    source_hashes_locked = {
        "config": core.sha256_bytes(config_bytes),
        "protocol_document": core.sha256_file(protocol_path),
        "ravel_runner": core.sha256_file(runner_path),
        "caper_dependency": core.sha256_file(core_path),
        "research_question": core.sha256_file(question_path),
        "cycle3_survey": core.sha256_file(survey_path),
    }
    protocol_sha = core.sha256_bytes(
        core.canonical_json_bytes(
            {
                "protocol_name": config["protocol_name"],
                "source_sha256": source_hashes_locked,
            }
        )
    )
    short = protocol_sha[:16]
    lock = RunnerLock(experiments_root / "ravel_poc.lock", protocol_sha)
    lock.acquire()
    run_directory: Path | None = None
    try:
        run_id = args.run_id or (
            "ravel-poc-v1-"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            + "-"
            + uuid.uuid4().hex[:12]
        )
        if Path(run_id).name != run_id or run_id in {"", ".", ".."}:
            raise ValueError("run-id must be one safe path component")
        run_directory = experiments_root / "ravel_poc_runs" / run_id
        run_directory.mkdir(parents=True, exist_ok=False)
        snapshots: dict[str, Path] = {}
        for label, source in (
            ("ravel_runner", runner_path),
            ("caper_dependency", core_path),
            ("protocol_document", protocol_path),
            ("research_question", question_path),
            ("cycle3_survey", survey_path),
        ):
            destination = run_directory / (
                f"{label}_{core.sha256_file(source)[:16]}_seq001{source.suffix}"
            )
            core.publish_bytes_no_overwrite(destination, source.read_bytes())
            snapshots[label] = destination
        effective_config = run_directory / (
            f"effective_config_{source_hashes_locked['config'][:16]}_seq001.json"
        )
        core.publish_bytes_no_overwrite(effective_config, config_bytes)
        environment_path = run_directory / f"environment_{short}_seq001.json"
        try:
            import faiss

            faiss_version = getattr(faiss, "__version__", "unknown")
        except ImportError:
            faiss_version = "missing"
        core.publish_json_no_overwrite(
            environment_path,
            {
                "schema": "ravel-environment-v1",
                "created_utc": core.utc_now(),
                "python_executable": sys.executable,
                "python_version": sys.version,
                "platform": platform.platform(),
                "numpy_version": np.__version__,
                "torch_version": torch.__version__,
                "faiss_version": faiss_version,
                "sentence_transformers_version": importlib.metadata.version(
                    "sentence-transformers"
                ),
                "scikit_learn_version": importlib.metadata.version("scikit-learn"),
                "thread_environment": THREAD_ENVIRONMENT,
                "hf_hub_offline": os.environ.get("HF_HUB_OFFLINE"),
                "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
                "source_snapshots": {
                    label: {
                        "file": path.name,
                        "sha256": core.sha256_file(path),
                    }
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
                {"utc": core.utc_now(), "event": event, "pid": os.getpid(), **values},
            )

        log_event(
            "run_started",
            protocol_sha256=protocol_sha,
            source_hashes=source_hashes_locked,
            thread_environment=THREAD_ENVIRONMENT,
        )
        archive_path = run_directory / "ml-1m.sha-locked.zip"
        dataset_sha, acquisition_mode = acquire_locked_archive(
            archive_path,
            str(config["dataset"]["official_url"]),
            str(config["dataset"]["expected_sha256"]),
            args.local_dataset_archive,
        )
        ratings_path, movies_path = core.extract_movielens(
            archive_path, run_directory / "sha_locked_ml1m_extracted"
        )
        dataset_source_hashes = {
            "archive": dataset_sha,
            "ratings.dat": core.sha256_file(ratings_path),
            "movies.dat": core.sha256_file(movies_path),
        }
        item_ids, metadata = core.load_movie_metadata(
            movies_path, str(config["embedding"]["metadata_template"])
        )
        item_to_index = {item_id: index for index, item_id in enumerate(item_ids)}
        interactions = core.load_ratings(ratings_path, item_to_index)
        splits, split_diagnostics = derive_ravel_cohort(
            interactions, config["dataset"]
        )
        a_splits, ar_splits, arv_splits = sealed_stage_views(splits)
        popularity = core.compute_train_popularity(a_splits, len(item_ids))
        popularity_path = run_directory / f"train_A_popularity_{short}_seq001.npy"
        core.save_numpy_no_overwrite(popularity_path, popularity)
        cohort_path = run_directory / f"cohort_lock_{short}_seq001.json"
        core.publish_json_no_overwrite(
            cohort_path,
            {
                "schema": "ravel-prospective-disjoint-cohort-v1",
                "protocol_sha256": protocol_sha,
                "diagnostics": split_diagnostics,
                "ravel_user_ids": [split.user_id for split in splits],
                "test_outcomes_inspected_for_replacement": False,
            },
        )
        log_event(
            "sha_locked_data_and_disjoint_cohort_derived",
            dataset_sha256=dataset_sha,
            acquisition_mode=acquisition_mode,
            ravel_users=len(splits),
            cohorts_disjoint=True,
        )

        semantic_vectors = core.encode_item_metadata(metadata, config["embedding"])
        semantic_matrix_path = run_directory / (
            f"semantic_item_matrix_{short}_seq001.npy"
        )
        semantic_index_path = run_directory / f"semantic_index_{short}_seq001.faiss"
        core.save_numpy_no_overwrite(semantic_matrix_path, semantic_vectors)
        semantic_index = core.build_faiss_index(semantic_vectors, config["retrieval"])
        core.publish_bytes_no_overwrite(
            semantic_index_path, core.serialize_faiss(semantic_index)
        )
        semantic_before = {
            "matrix_file": core.sha256_file(semantic_matrix_path),
            "matrix_memory": core.sha256_bytes(semantic_vectors.tobytes(order="C")),
            "index_file": core.sha256_file(semantic_index_path),
            "index_memory": core.sha256_bytes(core.serialize_faiss(semantic_index)),
        }

        seeds = [int(seed) for seed in config["replicate_seeds"]]
        seed_state: dict[int, dict[str, Any]] = {}
        matrix_records: list[dict[str, Any]] = []
        manifest_paths: list[Path] = []
        manifest_hashes: dict[str, str] = {}
        for seed in seeds:
            bprs: dict[str, BPRArtifacts] = {}
            indexes: dict[str, Any] = {}
            checkpoints: dict[str, str] = {}
            for variant in ("implicit", "rating_aware"):
                bpr, state = core.train_bpr(
                    a_splits, len(item_ids), variant, config["bpr"], seed
                )
                index = core.build_faiss_index(bpr.item_vectors, config["retrieval"])
                bprs[variant] = bpr
                indexes[variant] = index
                matrix_path = run_directory / (
                    f"bpr_{variant}_items_seed{seed}_{short}_seq001.npy"
                )
                user_path = run_directory / (
                    f"bpr_{variant}_users_seed{seed}_{short}_seq001.npy"
                )
                index_path = run_directory / (
                    f"bpr_{variant}_index_seed{seed}_{short}_seq001.faiss"
                )
                checkpoint_path = run_directory / (
                    f"bpr_{variant}_checkpoint_seed{seed}_{short}_seq001.pt"
                )
                core.save_numpy_no_overwrite(matrix_path, bpr.item_vectors)
                core.save_numpy_no_overwrite(user_path, bpr.user_vectors)
                core.publish_bytes_no_overwrite(
                    index_path, core.serialize_faiss(index)
                )
                core.save_torch_no_overwrite(
                    checkpoint_path,
                    {
                        "protocol_sha256": protocol_sha,
                        "seed": seed,
                        "variant": variant,
                        "state_dict": state,
                        "diagnostics": dict(bpr.training_diagnostics),
                    },
                )
                checkpoints[f"bpr_{variant}"] = checkpoint_path.name
                matrix_records.append(
                    {
                        "seed": seed,
                        "variant": variant,
                        "matrix_path": matrix_path,
                        "matrix": bpr.item_vectors,
                        "index_path": index_path,
                        "index": index,
                        "matrix_file_before": core.sha256_file(matrix_path),
                        "matrix_memory_before": core.sha256_bytes(
                            bpr.item_vectors.tobytes(order="C")
                        ),
                        "index_file_before": core.sha256_file(index_path),
                        "index_memory_before": core.sha256_bytes(
                            core.serialize_faiss(index)
                        ),
                    }
                )
            seed_state[seed] = {
                "bprs": bprs,
                "indexes": indexes,
                "alignment_manifests": {},
                "validation_manifests": {},
                "checkpoints": checkpoints,
            }
        log_event("all_A_models_and_immutable_indexes_fitted", seeds=seeds)

        # Publish every A-only R manifest before joining any R label.
        for seed in seeds:
            state = seed_state[seed]
            for variant in ("implicit", "rating_aware"):
                contexts, entries = core.build_prefix_candidate_manifest(
                    a_splits,
                    state["bprs"][variant],
                    state["indexes"][variant],
                    semantic_vectors,
                    semantic_index,
                    config,
                    "alignment",
                )
                split_by_user = {split.user_id: split for split in a_splits}
                collaborative_index_sha = core.sha256_bytes(
                    core.serialize_faiss(state["indexes"][variant])
                )
                entries = [
                    {
                        **dict(entry),
                        "candidate_context_provenance": candidate_context_provenance(
                            contexts[int(entry["user_id"])],
                            split_by_user[int(entry["user_id"])].train,
                            collaborative_index_sha,
                            str(semantic_before["index_memory"]),
                        ),
                    }
                    for entry in entries
                ]
                path = run_directory / (
                    f"alignment_manifest_{variant}_seed{seed}_{short}_seq001.json"
                )
                core.publish_json_no_overwrite(
                    path,
                    {
                        "schema": "ravel-target-blind-alignment-manifest-v1",
                        "protocol_sha256": protocol_sha,
                        "seed": seed,
                        "variant": variant,
                        "created_before_R_label_join": True,
                        "collaborative_index_memory_sha256": collaborative_index_sha,
                        "semantic_index_memory_sha256": semantic_before["index_memory"],
                        "entries": entries,
                    },
                )
                state["alignment_manifests"][variant] = contexts
                manifest_paths.append(path)
                manifest_hashes[path.name] = core.sha256_file(path)
        log_event("all_R_manifests_persisted_before_R_label_join")

        for seed in seeds:
            state = seed_state[seed]
            state["alignment_pair_pools"] = {}
            for variant in ("implicit", "rating_aware"):
                pair_keys, pair_rows = build_alignment_pair_pool(
                    ar_splits,
                    state["alignment_manifests"][variant],
                    int(config["dataset"]["preference_pair_minimum_rating_gap"]),
                    item_ids,
                )
                pair_path = run_directory / (
                    f"alignment_pair_pool_{variant}_seed{seed}_{short}_seq001.json"
                )
                core.publish_json_no_overwrite(
                    pair_path,
                    {
                        "schema": "ravel-natural-R-pair-pool-v1",
                        "protocol_sha256": protocol_sha,
                        "seed": seed,
                        "variant": variant,
                        "source_manifest_published_before_R_label_join": True,
                        "pairs": pair_rows,
                    },
                )
                state["alignment_pair_pools"][variant] = pair_keys
                manifest_paths.append(pair_path)
                manifest_hashes[pair_path.name] = core.sha256_file(pair_path)
        log_event("all_R_pair_pools_persisted_before_default_lock")

        # R is now legitimate prefix history. Publish every A+R V manifest
        # before any V outcome is used for identity, alpha, or routing.
        for seed in seeds:
            state = seed_state[seed]
            for variant in ("implicit", "rating_aware"):
                contexts, entries = core.build_prefix_candidate_manifest(
                    ar_splits,
                    state["bprs"][variant],
                    state["indexes"][variant],
                    semantic_vectors,
                    semantic_index,
                    config,
                    "validation",
                )
                split_by_user = {split.user_id: split for split in ar_splits}
                collaborative_index_sha = core.sha256_bytes(
                    core.serialize_faiss(state["indexes"][variant])
                )
                entries = [
                    {
                        **dict(entry),
                        "candidate_context_provenance": candidate_context_provenance(
                            contexts[int(entry["user_id"])],
                            (
                                *split_by_user[int(entry["user_id"])].train,
                                *split_by_user[int(entry["user_id"])].alignment,
                            ),
                            collaborative_index_sha,
                            str(semantic_before["index_memory"]),
                        ),
                    }
                    for entry in entries
                ]
                path = run_directory / (
                    f"validation_manifest_{variant}_seed{seed}_{short}_seq001.json"
                )
                core.publish_json_no_overwrite(
                    path,
                    {
                        "schema": "ravel-target-blind-validation-manifest-v1",
                        "protocol_sha256": protocol_sha,
                        "seed": seed,
                        "variant": variant,
                        "created_before_V_label_join": True,
                        "collaborative_index_memory_sha256": collaborative_index_sha,
                        "semantic_index_memory_sha256": semantic_before["index_memory"],
                        "entries": entries,
                    },
                )
                state["validation_manifests"][variant] = contexts
                manifest_paths.append(path)
                manifest_hashes[path.name] = core.sha256_file(path)
        log_event("all_V_manifests_persisted_before_first_V_use")

        # Segregated V use 1: lock only BPR identity and linear alpha.
        validation_bpr_by_seed: dict[int, Mapping[str, Mapping[str, float]]] = {}
        for seed in seeds:
            state = seed_state[seed]
            validation_bpr_by_seed[seed] = {
                variant: validation_bpr_metrics(
                    arv_splits, state["validation_manifests"][variant], config
                )
                for variant in ("implicit", "rating_aware")
            }
        bpr_validation_means = {
            variant: {
                metric: float(
                    np.mean(
                        [validation_bpr_by_seed[seed][variant][metric] for seed in seeds]
                    )
                )
                for metric in ("ndcg_at_10", "recall_at_10")
            }
            for variant in ("implicit", "rating_aware")
        }
        selected_bpr_variant = max(
            ("implicit", "rating_aware"),
            key=lambda variant: (
                bpr_validation_means[variant]["ndcg_at_10"],
                bpr_validation_means[variant]["recall_at_10"],
                variant == "implicit",
            ),
        )
        linear_grid_by_seed: dict[int, Mapping[str, Mapping[str, float]]] = {}
        for seed in seeds:
            state = seed_state[seed]
            state["selected_bpr"] = state["bprs"][selected_bpr_variant]
            state["selected_index"] = state["indexes"][selected_bpr_variant]
            linear_grid_by_seed[seed] = validation_linear_grid_metrics(
                arv_splits,
                state["validation_manifests"][selected_bpr_variant],
                state["selected_bpr"],
                semantic_vectors,
                popularity,
                config,
            )
        alpha_grid = [
            float(value) for value in config["residual"]["linear_fusion_validation_grid"]
        ]
        linear_validation_means = {
            str(value): {
                metric: float(
                    np.mean(
                        [linear_grid_by_seed[seed][str(value)][metric] for seed in seeds]
                    )
                )
                for metric in ("ndcg_at_10", "recall_at_10")
            }
            for value in alpha_grid
        }
        selected_linear_alpha = max(
            alpha_grid,
            key=lambda value: (
                linear_validation_means[str(value)]["ndcg_at_10"],
                linear_validation_means[str(value)]["recall_at_10"],
                value,
            ),
        )
        for seed in seeds:
            seed_state[seed]["linear_alpha"] = selected_linear_alpha
            seed_state[seed]["linear_grid"] = linear_grid_by_seed[seed]
        log_event(
            "segregated_V_use_1_default_identity_and_alpha_locked",
            selected_bpr_variant=selected_bpr_variant,
            bpr_validation_means=bpr_validation_means,
            selected_linear_alpha=selected_linear_alpha,
            linear_validation_means=linear_validation_means,
            test_used=False,
        )

        # Train the only residual on natural R pairs, using the now-frozen
        # linear score. V outcomes are not used by this training call.
        training_diagnostics: dict[str, Any] = {}
        for seed in seeds:
            state = seed_state[seed]
            corpus = build_uniform_linear_corpus(
                ar_splits,
                state["alignment_manifests"][selected_bpr_variant],
                state["selected_bpr"],
                semantic_vectors,
                popularity,
                float(state["linear_alpha"]),
                config,
                seed,
                item_ids,
                state["alignment_pair_pools"][selected_bpr_variant],
            )
            core.deterministic_setup(seed + 2100001)
            initial_model = BoundedResidual(
                int(corpus.chosen_features.shape[1]),
                int(config["residual"]["hidden_dimension"]),
                float(config["residual"]["residual_bound"]),
            )
            initial_state = {
                key: value.detach().clone()
                for key, value in initial_model.state_dict().items()
            }
            residual_model, residual_diagnostics = core.train_residual(
                corpus,
                initial_state,
                config["residual"],
                seed + 2200001,
                float(config["residual"]["simpo_margin"]),
                float(config["residual"]["soft_anchor_coefficient"]),
            )
            checkpoint_path = run_directory / (
                f"uniform_linear_residual_seed{seed}_{short}_seq001.pt"
            )
            core.save_torch_no_overwrite(
                checkpoint_path,
                {
                    "protocol_sha256": protocol_sha,
                    "seed": seed,
                    "state_dict": {
                        key: value.detach().cpu()
                        for key, value in residual_model.state_dict().items()
                    },
                    "diagnostics": residual_diagnostics,
                    "base_score": "frozen_linear_fusion",
                },
            )
            state["residual_model"] = residual_model
            state["checkpoints"]["uniform_linear_residual"] = checkpoint_path.name
            training_diagnostics[str(seed)] = {
                "validation_bpr": validation_bpr_by_seed[seed],
                "linear_alpha": state["linear_alpha"],
                "linear_grid": state["linear_grid"],
                "alignment_corpus": dict(corpus.diagnostics),
                "residual": residual_diagnostics,
                "linear_correct_pair_anchor_mask": True,
            }
        log_event("uniform_R_residuals_trained_and_frozen", test_used=False)

        # Segregated V use 2: fixed residual proposals produce outcomes for
        # cross-fitted selector calibration. No model below may inspect T.
        records_by_seed_spec: dict[int, dict[str, Sequence[Mapping[str, Any]]]] = {}
        proposal_rows_by_seed_spec: dict[
            int, dict[str, Sequence[Mapping[str, Any]]]
        ] = {}
        oof_by_seed_spec: dict[int, dict[str, Mapping[Any, Mapping[str, float]]]] = {}
        oof_diagnostics: dict[str, Any] = {}
        for seed in seeds:
            state = seed_state[seed]
            records_by_seed_spec[seed] = {}
            proposal_rows_by_seed_spec[seed] = {}
            oof_by_seed_spec[seed] = {}
            oof_diagnostics[str(seed)] = {}
            for tie_width in map(float, config["proposal"]["near_tie_width_grid"]):
                for regret_budget in map(
                    float, config["proposal"]["linear_regret_budget_grid"]
                ):
                    spec = proposal_spec_key(tie_width, regret_budget)
                    proposal_rows = build_validation_proposal_rows(
                        ar_splits,
                        state["validation_manifests"][selected_bpr_variant],
                        state["selected_bpr"],
                        semantic_vectors,
                        popularity,
                        state["residual_model"],
                        float(state["linear_alpha"]),
                        tie_width,
                        regret_budget,
                        config,
                    )
                    proposal_rows_by_seed_spec[seed][spec] = proposal_rows
                    proposal_path = run_directory / (
                        f"validation_proposals_seed{seed}_"
                        f"{core.sha256_bytes(spec.encode('utf-8'))[:12]}_{short}_seq001.json"
                    )
                    core.publish_json_no_overwrite(
                        proposal_path,
                        {
                            "schema": "ravel-target-blind-validation-proposals-v1",
                            "protocol_sha256": protocol_sha,
                            "seed": seed,
                            "specification": spec,
                            "created_before_full_V_label_join": True,
                            "entries": serialize_validation_proposal_rows(
                                proposal_rows, tie_width, regret_budget
                            ),
                        },
                    )
                    manifest_paths.append(proposal_path)
                    manifest_hashes[proposal_path.name] = core.sha256_file(proposal_path)
        log_event("all_registered_V_proposals_persisted_before_full_V_label_join")
        for seed in seeds:
            for tie_width in map(float, config["proposal"]["near_tie_width_grid"]):
                for regret_budget in map(
                    float, config["proposal"]["linear_regret_budget_grid"]
                ):
                    spec = proposal_spec_key(tie_width, regret_budget)
                    joined = join_validation_proposal_outcomes(
                        arv_splits,
                        proposal_rows_by_seed_spec[seed][spec],
                        config,
                        item_ids,
                    )
                    records = [{**dict(row), "seed": seed} for row in joined]
                    records_by_seed_spec[seed][spec] = records
        for tie_width in map(float, config["proposal"]["near_tie_width_grid"]):
            for regret_budget in map(
                float, config["proposal"]["linear_regret_budget_grid"]
            ):
                spec = proposal_spec_key(tie_width, regret_budget)
                combined = [
                    row for seed in seeds for row in records_by_seed_spec[seed][spec]
                ]
                predictions, diagnostics = crossfit_router(
                    combined, config["selector"]
                )
                for seed in seeds:
                    oof_by_seed_spec[seed][spec] = predictions
                    oof_diagnostics[str(seed)][spec] = {
                        **dict(diagnostics),
                        "shared_across_all_seed_rows": True,
                    }
        all_validation_oof_rows: list[Mapping[str, Any]] = []
        for seed in seeds:
            for spec in sorted(records_by_seed_spec[seed]):
                predictions = oof_by_seed_spec[seed][spec]
                for row in records_by_seed_spec[seed][spec]:
                    user_id = int(row["user_id"])
                    prediction = predictions[(seed, user_id)]
                    all_validation_oof_rows.append(
                        {
                            "seed": seed,
                            "specification": spec,
                            "user_id": user_id,
                            "proposal_changed": bool(row["proposal_changed"]),
                            "near_tie_tightness": float(
                                row["near_tie_tightness"]
                            ),
                            "uncertainty_score": float(row["uncertainty_score"]),
                            "preference_delta": (
                                float(row["preference_delta"])
                                if math.isfinite(float(row["preference_delta"]))
                                else None
                            ),
                            "ndcg_delta": float(row["ndcg_delta"]),
                            "harmful": bool(row["harmful"]),
                            "benefit_probability": float(
                                prediction["benefit_probability"]
                            ),
                            "harm_probability": float(
                                prediction["harm_probability"]
                            ),
                            "single_head_probability": float(
                                prediction["single_head_probability"]
                            ),
                        }
                    )
        all_validation_oof_path = run_directory / (
            f"all_validation_oof_evidence_{short}_seq001.json"
        )
        core.publish_json_no_overwrite(
            all_validation_oof_path,
            {
                "schema": "ravel-all-validation-oof-evidence-v1",
                "protocol_sha256": protocol_sha,
                "rows": all_validation_oof_rows,
                "test_outcomes_used": False,
            },
        )
        manifest_paths.append(all_validation_oof_path)
        manifest_hashes[all_validation_oof_path.name] = core.sha256_file(
            all_validation_oof_path
        )
        selection = select_validation_policy(
            records_by_seed_spec, oof_by_seed_spec, config
        )
        selected_spec = proposal_spec_key(
            float(selection["tie_width"]),
            float(selection["linear_regret_budget"]),
        )
        selected_all_seed_records = [
            row
            for seed in seeds
            for row in records_by_seed_spec[seed][selected_spec]
        ]
        selected_validation_oof_rows: list[Mapping[str, Any]] = []
        for seed in seeds:
            predictions = oof_by_seed_spec[seed][selected_spec]
            for row in records_by_seed_spec[seed][selected_spec]:
                user_id = int(row["user_id"])
                prediction = predictions[(seed, user_id)]
                accepted = bool(
                    row["proposal_changed"]
                    and prediction["benefit_probability"]
                    >= float(selection["benefit_probability_threshold"])
                    and prediction["harm_probability"]
                    <= float(selection["maximum_harm_probability"])
                )
                selected_validation_oof_rows.append(
                    {
                        "seed": seed,
                        "user_id": user_id,
                        "proposal_changed": bool(row["proposal_changed"]),
                        "preference_pairs": int(row["preference_pairs"]),
                        "preference_delta": (
                            float(row["preference_delta"])
                            if math.isfinite(float(row["preference_delta"]))
                            else None
                        ),
                        "ndcg_delta": float(row["ndcg_delta"]),
                        "harmful": bool(row["harmful"]),
                        "benefit_probability": float(
                            prediction["benefit_probability"]
                        ),
                        "harm_probability": float(prediction["harm_probability"]),
                        "accepted": accepted,
                    }
                )
        selected_validation_oof_path = run_directory / (
            f"selected_validation_oof_evidence_{short}_seq001.json"
        )
        core.publish_json_no_overwrite(
            selected_validation_oof_path,
            {
                "schema": "ravel-selected-validation-oof-evidence-v1",
                "protocol_sha256": protocol_sha,
                "selected_specification": selected_spec,
                "benefit_probability_threshold": selection[
                    "benefit_probability_threshold"
                ],
                "maximum_harm_probability": selection[
                    "maximum_harm_probability"
                ],
                "rows": selected_validation_oof_rows,
                "test_outcomes_used": False,
            },
        )
        manifest_paths.append(selected_validation_oof_path)
        manifest_hashes[selected_validation_oof_path.name] = core.sha256_file(
            selected_validation_oof_path
        )
        global_router = fit_full_router(
            selected_all_seed_records, config["selector"]
        )
        for seed in seeds:
            seed_state[seed]["router"] = global_router
        selector_lock_path = run_directory / f"selector_lock_{short}_seq001.json"
        core.publish_json_no_overwrite(
            selector_lock_path,
            {
                "schema": "ravel-validation-locked-selector-v1",
                "protocol_sha256": protocol_sha,
                "created_before_any_T_manifest": True,
                "segregated_V_use": "proposal outcomes and cross-fitted selector only",
                "selection": selection,
                "all_validation_oof_evidence_file": all_validation_oof_path.name,
                "all_validation_oof_evidence_sha256": core.sha256_file(
                    all_validation_oof_path
                ),
                "selected_validation_oof_evidence_file": (
                    selected_validation_oof_path.name
                ),
                "selected_validation_oof_evidence_sha256": core.sha256_file(
                    selected_validation_oof_path
                ),
                "router_shared_across_seed_rows": global_router.serializable(),
                "label_reliability_features_used": False,
                "single_head_is_post_training_ablation_not_joint_residual_training": True,
                "test_outcomes_used": False,
            },
        )
        selector_lock_sha = core.sha256_file(selector_lock_path)
        log_event(
            "segregated_V_use_2_selector_and_controls_locked",
            selector_lock_sha256=selector_lock_sha,
            selected_spec=selected_spec,
            test_used=False,
        )

        # Every target-blind candidate, proposal, decision, output ranking, and
        # full-union scalar score is published for every seed before T opens.
        test_manifests: dict[int, Mapping[int, TestPolicyEntry]] = {}
        test_manifest_records: dict[str, Any] = {}
        for seed in seeds:
            state = seed_state[seed]
            candidates, candidate_serializable = core.build_test_candidate_manifest(
                arv_splits,
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
            policy_manifest, serializable = build_test_policy_manifest(
                arv_splits,
                candidates,
                state["selected_bpr"],
                semantic_vectors,
                popularity,
                state["residual_model"],
                state["router"],
                float(state["linear_alpha"]),
                selection,
                seed,
                config,
            )
            candidate_rows = {
                int(record["user_id"]): dict(record)
                for record in candidate_serializable
            }
            split_by_user = {split.user_id: split for split in arv_splits}
            collaborative_index_sha = core.sha256_bytes(
                core.serialize_faiss(state["selected_index"])
            )
            implicit_index_sha = core.sha256_bytes(
                core.serialize_faiss(state["indexes"]["implicit"])
            )
            rating_index_sha = core.sha256_bytes(
                core.serialize_faiss(state["indexes"]["rating_aware"])
            )
            enriched_serializable: list[Mapping[str, Any]] = []
            for record in serializable:
                user_id = int(record["user_id"])
                split = split_by_user[user_id]
                candidate_entry = candidates[user_id]
                candidate_record = candidate_rows[user_id]
                candidate_record["candidate_context_provenance"] = (
                    candidate_context_provenance(
                        candidate_entry.context,
                        (*split.train, *split.alignment, *split.validation),
                        collaborative_index_sha,
                        str(semantic_before["index_memory"]),
                        {
                            "implicit_bpr": candidate_entry.implicit_query,
                            "rating_aware_bpr": candidate_entry.rating_aware_query,
                        },
                    )
                )
                enriched_serializable.append(
                    {**dict(record), "candidate_manifest": candidate_record}
                )
            serializable = enriched_serializable
            path = run_directory / f"test_output_manifest_seed{seed}_{short}_seq001.json"
            core.publish_json_no_overwrite(
                path,
                {
                    "schema": "ravel-target-blind-test-output-manifest-v1",
                    "protocol_sha256": protocol_sha,
                    "seed": seed,
                    "selected_bpr_variant": selected_bpr_variant,
                    "linear_alpha": state["linear_alpha"],
                    "selector_lock_file": selector_lock_path.name,
                    "selector_lock_sha256": selector_lock_sha,
                    "created_before_T_label_join": True,
                    "full_union_ranking_and_score_bits_persisted": True,
                    "collaborative_index_memory_sha256": collaborative_index_sha,
                    "implicit_index_memory_sha256": implicit_index_sha,
                    "rating_aware_index_memory_sha256": rating_index_sha,
                    "semantic_index_memory_sha256": semantic_before["index_memory"],
                    "entries": serializable,
                },
            )
            manifest_paths.append(path)
            manifest_hashes[path.name] = core.sha256_file(path)
            test_manifest_records[str(seed)] = {
                "file": path.name,
                "sha256": core.sha256_file(path),
                "entries": len(serializable),
            }
            test_manifests[seed] = policy_manifest
        log_event("all_seed_T_output_manifests_persisted_before_any_T_label_join")

        # Latency is target blind and is measured after all choices are frozen,
        # still before the single explicit T outcome join.
        latency_by_seed: dict[int, Mapping[str, Any]] = {}
        for seed in seeds:
            state = seed_state[seed]
            latency_by_seed[seed] = benchmark_latency(
                arv_splits,
                state["selected_bpr"],
                state["selected_index"],
                semantic_vectors,
                semantic_index,
                popularity,
                state["residual_model"],
                state["router"],
                float(state["linear_alpha"]),
                selection,
                config,
            )
        latency_evidence_path = run_directory / (
            f"target_blind_latency_evidence_{short}_seq001.json"
        )
        measured_user_ids = [
            int(split.user_id)
            for split in sorted(arv_splits, key=lambda split: split.user_id)[
                : int(config["evaluation"]["latency_measured_users"])
            ]
        ]
        core.publish_json_no_overwrite(
            latency_evidence_path,
            {
                "schema": "ravel-target-blind-latency-evidence-v1",
                "protocol_sha256": protocol_sha,
                "created_before_T_label_join": True,
                "test_labels_or_item_identities_joined": False,
                "measured_user_ids_numeric_order": measured_user_ids,
                "warmup_user_ids_also_measured": measured_user_ids[
                    : int(config["evaluation"]["latency_warmup_users"])
                ],
                "repetitions": int(config["evaluation"]["latency_repetitions"]),
                "interleaving": "AB/BA by (repetition + numeric-user-position) parity",
                "per_seed_raw_user_medians_and_summaries": {
                    str(seed): latency_by_seed[seed] for seed in seeds
                },
            },
        )
        manifest_paths.append(latency_evidence_path)
        manifest_hashes[latency_evidence_path.name] = core.sha256_file(
            latency_evidence_path
        )
        log_event(
            "target_blind_latency_evidence_persisted_before_T_label_join",
            file=latency_evidence_path.name,
            sha256=manifest_hashes[latency_evidence_path.name],
        )

        # The only T-label join in the runner.
        per_seed_rows: dict[int, Mapping[str, list[Mapping[str, Any]]]] = {}
        per_seed_diagnostics: dict[int, Mapping[str, Any]] = {}
        log_event("sealed_T_opened_once_for_final_evaluation")
        for seed in seeds:
            rows, diagnostics = evaluate_test_seed(
                splits, test_manifests[seed], config, item_ids
            )
            per_seed_rows[seed] = rows
            per_seed_diagnostics[seed] = diagnostics
            del test_manifests[seed]

        semantic_after = {
            "matrix_file": core.sha256_file(semantic_matrix_path),
            "matrix_memory": core.sha256_bytes(semantic_vectors.tobytes(order="C")),
            "index_file": core.sha256_file(semantic_index_path),
            "index_memory": core.sha256_bytes(core.serialize_faiss(semantic_index)),
        }
        semantic_unchanged = semantic_before == semantic_after
        matrix_audit: list[Mapping[str, Any]] = []
        for record in matrix_records:
            after = {
                "matrix_file_after": core.sha256_file(record["matrix_path"]),
                "matrix_memory_after": core.sha256_bytes(
                    record["matrix"].tobytes(order="C")
                ),
                "index_file_after": core.sha256_file(record["index_path"]),
                "index_memory_after": core.sha256_bytes(
                    core.serialize_faiss(record["index"])
                ),
            }
            unchanged = bool(
                record["matrix_file_before"] == after["matrix_file_after"]
                and record["matrix_memory_before"] == after["matrix_memory_after"]
                and record["index_file_before"] == after["index_file_after"]
                and record["index_memory_before"] == after["index_memory_after"]
            )
            matrix_audit.append(
                {
                    "seed": record["seed"],
                    "variant": record["variant"],
                    "matrix_file": record["matrix_path"].name,
                    "index_file": record["index_path"].name,
                    "matrix_file_before": record["matrix_file_before"],
                    "matrix_memory_before": record["matrix_memory_before"],
                    "index_file_before": record["index_file_before"],
                    "index_memory_before": record["index_memory_before"],
                    **after,
                    "unchanged": unchanged,
                }
            )
        immutable = semantic_unchanged and all(
            bool(record["unchanged"]) for record in matrix_audit
        )
        manifests_stable = bool(
            len(manifest_paths) == len(manifest_hashes)
            and all(
                path.is_file()
                and manifest_hashes[path.name] == core.sha256_file(path)
                for path in manifest_paths
            )
            and core.sha256_file(selector_lock_path) == selector_lock_sha
        )
        sources_stable = bool(
            core.sha256_file(config_path) == source_hashes_locked["config"]
            and core.sha256_file(effective_config) == source_hashes_locked["config"]
            and core.sha256_file(protocol_path)
            == source_hashes_locked["protocol_document"]
            and core.sha256_file(runner_path) == source_hashes_locked["ravel_runner"]
            and core.sha256_file(core_path) == source_hashes_locked["caper_dependency"]
            and core.sha256_file(question_path) == source_hashes_locked["research_question"]
            and core.sha256_file(survey_path) == source_hashes_locked["cycle3_survey"]
            and all(
                core.sha256_file(snapshots[label]) == source_hashes_locked[label]
                for label in snapshots
            )
            and core.sha256_file(archive_path) == dataset_sha
            and core.sha256_file(ratings_path) == dataset_source_hashes["ratings.dat"]
            and core.sha256_file(movies_path) == dataset_source_hashes["movies.dat"]
        )
        integrity = {
            "cohort_disjointness": bool(split_diagnostics["cohorts_disjoint"]),
            "immutable": immutable,
            "manifests_stable": manifests_stable,
            "temporal_and_provenance": bool(
                split_diagnostics["timestamp_groups_indivisible"]
                and split_diagnostics["strict_temporal_boundaries"]
                and config["dataset"]["exclude_demographics"]
                and dataset_sha == config["dataset"]["expected_sha256"]
            ),
            "source_hashes_stable": sources_stable,
            "async_ledger_empty": error_ledger.stat().st_size == 0,
        }
        promise_gate = evaluate_ten_part_gate(
            per_seed_rows,
            per_seed_diagnostics,
            latency_by_seed,
            selection,
            integrity,
            config,
        )
        execution_sha = core.sha256_bytes(
            core.canonical_json_bytes(
                {
                    "protocol_sha256": protocol_sha,
                    "dataset_sha256": dataset_sha,
                    "cohort_sha256": core.sha256_file(cohort_path),
                    "selected_bpr_variant": selected_bpr_variant,
                    "selection": selection,
                    "seeds": seeds,
                }
            )
        )
        execution_short = execution_sha[:16]
        per_user_path = run_directory / (
            f"per_user_metrics_{execution_short}_seq001.csv"
        )
        core.publish_bytes_no_overwrite(
            per_user_path, per_user_csv_bytes(per_seed_rows)
        )
        result = {
            "schema": "ravel-poc-result-v1",
            "status": "COMPLETE_RUNNER_RESULT",
            "protocol_name": config["protocol_name"],
            "protocol_sha256": protocol_sha,
            "execution_fingerprint_sha256": execution_sha,
            "created_utc": core.utc_now(),
            "run_directory": str(run_directory),
            "dataset_sha256": dataset_sha,
            "scientific_protocol": {
                "cohort": "SHA-order eligible users [1000:2000], disjoint from CAPER [0:1000]",
                "split": "per-user indivisible timestamp groups A/R/V/T=60/20/10/10",
                "default": "validation-selected BPR and projected linear semantic-collaborative fusion",
                "residual": (
                    "uniform natural R-pair SimPO-derived bounded residual with frozen "
                    "linear base and linear-correct-pair anchor"
                ),
                "proposal": (
                    "Q95-Q05-normalized near-tie membership swaps, deterministic hard "
                    "precedence ordering, unweighted normalized top10 linear-score regret, "
                    "and an unchanged frozen-linear nonselected tail"
                ),
                "selector": (
                    "two cross-fitted fold-standardized class-balanced logistic heads; "
                    "benefit refit on pair-bearing V and harm refit on relevance-eligible "
                    "V; label-free 14-d request descriptor"
                ),
                "preference_accuracy": (
                    "final served full-union order with a constrained top-10 prefix and "
                    "unchanged frozen-linear nonselected tail"
                ),
                "exact_fallback": (
                    "same cached full-union item order and corresponding float32 "
                    "score bytes and SHA-256"
                ),
                "test_set_used_for_selection": False,
            },
            "selection_locks": {
                "selected_bpr_variant": selected_bpr_variant,
                "bpr_validation_means": bpr_validation_means,
                "linear_alpha_by_seed": {
                    str(seed): seed_state[seed]["linear_alpha"] for seed in seeds
                },
                "selector_and_controls": selection,
                "selector_lock_file": selector_lock_path.name,
                "selector_lock_sha256": selector_lock_sha,
                "all_locked_before_any_T_manifest": True,
            },
            "promise_gate": promise_gate,
            "per_seed_method_summaries": {
                str(seed): {
                    method: summarize_rows(per_seed_rows[seed][method])
                    for method in METHODS
                }
                for seed in seeds
            },
            "per_seed_diagnostics": {
                str(seed): per_seed_diagnostics[seed] for seed in seeds
            },
            "latency_by_seed": {
                str(seed): latency_by_seed[seed] for seed in seeds
            },
            "training_diagnostics": training_diagnostics,
            "crossfit_diagnostics": oof_diagnostics,
            "data_counts": {
                "catalog_items": len(item_ids),
                "interactions": len(interactions),
                "ravel_users": len(splits),
                "split_diagnostics": split_diagnostics,
            },
            "provenance": {
                "acquisition_mode": acquisition_mode,
                "official_url": config["dataset"]["official_url"],
                "dataset_source_hashes": dataset_source_hashes,
                "source_hashes": source_hashes_locked,
                "environment_file": environment_path.name,
                "effective_config_file": effective_config.name,
                "cohort_file": cohort_path.name,
                "candidate_manifests": {
                    "files": [path.name for path in manifest_paths],
                    "sha256": {
                        path.name: core.sha256_file(path) for path in manifest_paths
                    },
                    "test": test_manifest_records,
                    "R_persisted_before_R_label_join": True,
                    "V_persisted_before_V_label_join": True,
                    "T_outputs_persisted_before_T_label_join": True,
                    "target_injection_count": 0,
                },
            },
            "immutability": {
                "semantic_before": semantic_before,
                "semantic_after": semantic_after,
                "semantic_unchanged": semantic_unchanged,
                "collaborative": matrix_audit,
                "all_unchanged": immutable,
            },
            "integrity": integrity,
            "known_limitations": [
                "No conformal, causal, distribution-free, or true-utility safety claim.",
                "The selector uses label-free request descriptors; historical reliability features are deferred.",
                "The single-head diagnostic is post-training and is not a jointly trained residual/gate control.",
                "MovieLens exact-index latency does not establish million-item production latency.",
            ],
            "artifacts": {
                "per_user_metrics": per_user_path.name,
                "checkpoints": {
                    str(seed): seed_state[seed]["checkpoints"] for seed in seeds
                },
            },
            "completion_semantics": (
                "Runner result is a candidate only. Completion additionally requires "
                "process exit, lock release, empty asynchronous ledger, recursive hash "
                "verification, and one external post-exit marker."
            ),
        }
        result_path = run_directory / f"result_{execution_short}_seq001.json"
        core.publish_json_no_overwrite(result_path, result)
        log_event(
            "result_published",
            result_file=result_path.name,
            promise_gate_passed=bool(promise_gate["passed"]),
        )
        if error_ledger.stat().st_size != 0:
            raise IntegrityError("Async ledger is nonempty; refusing completion candidate")
        log_event("runner_artifacts_finalized")
        artifact_hashes = core.collect_artifact_hashes(run_directory)
        completion_marker = run_directory / (
            f"RUNNER_COMPLETE_CANDIDATE_{execution_short}.json"
        )
        core.publish_json_no_overwrite(
            completion_marker,
            {
                "schema": "ravel-runner-completion-candidate-v1",
                "created_utc": core.utc_now(),
                "pid": os.getpid(),
                "run_directory": str(run_directory),
                "protocol_sha256": protocol_sha,
                "config_sha256": source_hashes_locked["config"],
                "runner_sha256": source_hashes_locked["ravel_runner"],
                "execution_fingerprint_sha256": execution_sha,
                "result_file": result_path.name,
                "result_sha256": artifact_hashes[result_path.name],
                "asynchronous_error_ledger": error_ledger.name,
                "asynchronous_error_ledger_sha256": artifact_hashes[
                    error_ledger.name
                ],
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
                f"synchronous_error_{short}_"
                f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}_"
                f"{uuid.uuid4().hex}.json"
            )
            try:
                core.publish_json_no_overwrite(
                    error_path,
                    {
                        "schema": "ravel-synchronous-error-v1",
                        "utc": core.utc_now(),
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


def synthetic_self_test(config: Mapping[str, Any]) -> Mapping[str, Any]:
    """Outcome-free checks for projection, routing, and exact fallback."""
    validate_config(config)
    items = tuple(range(20))
    scores = np.linspace(1.0, 0.0, len(items), dtype=np.float32)
    features = np.zeros((len(items), 13), dtype=np.float32)
    features[:, 4] = np.linspace(0.0, 1.0, len(items), dtype=np.float32)
    features[:, 5] = features[:, 4]
    features[:, 10] = 0.5
    linear = LinearDefault(
        items=items,
        ranking=items,
        scores=scores,
        bpr_scores=scores.copy(),
        semantic_scores=scores.copy(),
        features=features,
    )
    residual = np.zeros(len(items), dtype=np.float32)
    residual[10] = 0.25
    residual[9] = -0.25
    proposal = make_proposal(linear, residual, 0.2, 0.12, config)
    fallback = _policy_output(linear, proposal, False)
    fallback_record = canonical_full_union_record(
        linear.items, fallback.ranking, fallback.scores
    )
    linear_record = canonical_full_union_record(
        linear.items, linear.ranking, linear.scores
    )
    if (
        fallback.ranking != linear.ranking
        or fallback.scores.tobytes() != linear.scores.tobytes()
        or fallback_record != linear_record
        or core.sha256_bytes(fallback_record) != core.sha256_bytes(linear_record)
        or not fallback.exact_fallback
    ):
        raise AssertionError("Synthetic exact fallback failed")
    selector = config["selector"]
    matrix = np.vstack(
        [np.linspace(-1.0, 1.0, 14) + index / 10.0 for index in range(20)]
    )
    labels = np.asarray([index % 2 for index in range(20)], dtype=np.int64)
    router = fit_binary_router(matrix, labels, selector)
    predictions = router.predict(matrix[:3])
    if not np.all((predictions > 0.0) & (predictions < 1.0)):
        raise AssertionError("Synthetic router probabilities failed")
    sample_catalog_ids = (900, 10, 500, 20)
    sample_events = (
        Interaction(1, 0, 5, 1, 0),
        Interaction(1, 1, 1, 2, 1),
        Interaction(1, 2, 4, 3, 2),
        Interaction(1, 3, 2, 4, 3),
    )
    selected_pairs, raw_pairs = preference_pairs_by_movie_id(
        sample_events, 2, 1, 20261118, 1, sample_catalog_ids
    )
    if raw_pairs < 2 or len(selected_pairs) != 1:
        raise AssertionError("Movie-ID preference-pair hash cap failed")
    jaccard_descriptor = request_descriptor(
        linear,
        scores,
        np.zeros(len(items), dtype=bool),
        1,
        0.0,
        1.0,
        0.12,
        1.0,
        0.0,
        tuple(range(5, 15)),
    )
    if not math.isclose(float(jaccard_descriptor[7]), 5.0 / 15.0, abs_tol=1e-12):
        raise AssertionError("Selector overlap feature is not top-10 Jaccard")
    zero_swap_residual = np.zeros(len(items), dtype=np.float32)
    zero_swap_residual[19] = 0.2
    zero_swap = make_proposal(linear, zero_swap_residual, 0.025, 0.12, config)
    if zero_swap.swap_count != 0 or float(zero_swap.descriptor[11]) != 0.0:
        raise AssertionError("Zero-swap sign-agreement convention failed")
    expected_tail = tuple(
        item for item in linear.ranking if item not in set(proposal.ranking[:10])
    )
    if tuple(proposal.ranking[10:]) != expected_tail:
        raise AssertionError("Finite proposal changed the unconstrained linear tail")
    always_on = _always_on_policy_output(proposal)
    if (
        not always_on.accepted
        or always_on.ranking != proposal.ranking
        or always_on.scores.tobytes(order="C")
        != proposal.scores.tobytes(order="C")
    ):
        raise AssertionError("Always-on control did not serve the selected proposal")
    synthetic_context = CandidateContext(
        user_id=1,
        collaborative=(0, 1),
        semantic=(1, 2),
        union=(0, 1, 2),
        semantic_query=np.asarray([0.5, 0.5], dtype=np.float32),
        dislike_query=np.asarray([0.0, 1.0], dtype=np.float32),
        collaborative_query=np.asarray([1.0, 0.0], dtype=np.float32),
        history_log_feature=0.25,
        bpr_min=-0.5,
        bpr_span=1.0,
        semantic_min=-0.25,
        semantic_span=0.75,
        collaborative_rank={0: 0, 1: 1},
        semantic_rank={1: 0, 2: 1},
        regret_scale_degenerate=False,
    )
    provenance = candidate_context_provenance(
        synthetic_context,
        (Interaction(1, 3, 5, 1, 0),),
        "a" * 64,
        "b" * 64,
    )
    query_record = provenance["query_records"]["collaborative"]
    if (
        core.sha256_bytes(bytes.fromhex(str(query_record["bytes_hex"])))
        != query_record["sha256"]
        or not provenance["seen_filter"]["all_candidates_unseen"]
        or provenance["branch_rank_by_union_position"]["collaborative"]
        != [0, 1, -1]
    ):
        raise AssertionError("Candidate provenance record is not replayable")
    synthetic_support_rows = {
        1: {
            "ravel": [
                {
                    "user_id": 1,
                    "accepted": 1.0,
                    "preference_pair_accuracy": 1.0,
                },
                {
                    "user_id": 2,
                    "accepted": 0.0,
                    "preference_pair_accuracy": float("nan"),
                },
                {
                    "user_id": 3,
                    "accepted": 0.0,
                    "preference_pair_accuracy": 1.0,
                },
            ]
        },
        2: {
            "ravel": [
                {
                    "user_id": 1,
                    "accepted": 0.0,
                    "preference_pair_accuracy": float("nan"),
                },
                {
                    "user_id": 2,
                    "accepted": 1.0,
                    "preference_pair_accuracy": 0.0,
                },
                {
                    "user_id": 3,
                    "accepted": 1.0,
                    "preference_pair_accuracy": float("nan"),
                },
            ]
        },
    }
    if not math.isclose(
        accepted_pair_bearing_support(synthetic_support_rows), 1.0, abs_tol=1e-12
    ):
        raise AssertionError("Accepted pair-bearing support mixed seed rows")
    return {
        "config_valid": True,
        "projection_regret_within_budget": proposal.linear_regret <= 0.12 + 1e-7,
        "exact_fallback": True,
        "selector_jaccard_and_zero_swap_conventions": True,
        "finite_proposal_linear_tail_preserved": True,
        "always_on_same_selected_proposal": True,
        "candidate_provenance_replayable": True,
        "accepted_pair_support_same_seed_conjunction": True,
        "router_probabilities_finite": True,
        "movie_id_pair_hash_cap": True,
        "sealed_outcomes_accessed": False,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Run the preregistered RAVEL MovieLens-1M proof of concept."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=project_root / "src" / "configs" / "ravel_poc_ml1m_v1.json",
        help="Immutable JSON protocol configuration.",
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
        help="Root containing the RAVEL lock and append-only run directories.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional unique safe run-directory component supplied by the launcher.",
    )
    parser.add_argument(
        "--local-dataset-archive",
        type=Path,
        default=None,
        help="Optional local ML-1M archive; SHA-256 must match the locked official file.",
    )
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate the config without accessing data or outcomes.",
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
    completion = execute(args)
    if not completion.is_file():
        raise IntegrityError("RAVEL runner returned without a completion candidate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
