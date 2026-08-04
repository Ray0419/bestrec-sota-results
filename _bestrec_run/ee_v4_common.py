#!/usr/bin/env python3
"""Frozen common machinery for the E-E V4 normal-init SASRec sensitivity."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import torch

import ee_v3_common as base


ROOT = base.ROOT
HERE = base.HERE
PRIVATE = HERE / "ee_v4_private"
UPSTREAM = base.UPSTREAM
DATA = base.DATA
TRAIN_VALID_INPUT = base.TRAIN_VALID_INPUT
PROTOCOL = "PREREG_EE_V4"
UPSTREAM_URL = base.UPSTREAM_URL
UPSTREAM_COMMIT = base.UPSTREAM_COMMIT
UPSTREAM_SOURCE_HASHES = base.UPSTREAM_SOURCE_HASHES
DATA_HASHES = base.DATA_HASHES
TRAIN_VALID_INPUT_SHA256 = base.TRAIN_VALID_INPUT_SHA256
EEV3_ADJUDICATION = HERE / "ee_v3_adjudication.json"
EEV3_ADJUDICATION_SHA256 = "978aebe051abdefe3de542856bad6e321f6d581c53edfa9c01594006d24126ef"

ARMS = ("sasrec_normal",)
MODEL_TYPES = {"sasrec_normal": "SASRec"}
SEEDS = tuple(range(20262301, 20262309))
TRAIN_WAVES = tuple(tuple(SEEDS[i:i + 2]) for i in range(0, len(SEEDS), 2))
N_USERS = base.N_USERS
N_ITEMS = base.N_ITEMS
MAX_LEN = base.MAX_LEN
BATCH_SIZE = base.BATCH_SIZE
MAX_EPOCHS = base.MAX_EPOCHS
PATIENCE = base.PATIENCE

utc_now = base.utc_now
sha256 = base.sha256
atomic_json = base.atomic_json
exclusive_json = base.exclusive_json
atomic_torch = base.atomic_torch
atomic_npz = base.atomic_npz
verify_upstream = base.verify_upstream
verify_data = base.verify_data
repository_head = base.repository_head
load_json = base.load_json
set_seed = base.set_seed
environment = base.environment
SeqDataset = base.SeqDataset
load_train_frame = base.load_train_frame
load_train_histories = base.load_train_histories
load_eval_inputs = base.load_eval_inputs
ranks_from_scores = base.ranks_from_scores
metric_family = base.metric_family
evaluate_model = base.evaluate_model


def expected_pairs() -> tuple[tuple[str, int], ...]:
    return tuple((arm, seed) for arm in ARMS for seed in SEEDS)


def key_words(arm: str, seed: int) -> dict[str, object]:
    if arm not in ARMS or seed not in SEEDS:
        raise RuntimeError("unknown E-E V4 arm/seed")
    value = base.key_words("sasrec_id", base.SEEDS[0]).copy()
    value["random_seed"] = seed
    value["ID_embs_init_type"] = "normal"
    value["model_type"] = "SASRec"
    return value


def build_model(arm: str, seed: int, device: torch.device):
    verify_upstream()
    source = str(UPSTREAM)
    if source not in sys.path:
        sys.path.insert(0, source)
    from models.backbone_SASRec import SASRec
    return SASRec(device, **key_words(arm, seed)).to(device)


def training_path(arm: str, seed: int) -> Path:
    return PRIVATE / f"training_EEV4_{arm}_seed{seed}.json"


def started_path(arm: str, seed: int) -> Path:
    return PRIVATE / f"training_EEV4_{arm}_seed{seed}.started.json"


def best_path(arm: str, seed: int) -> Path:
    return PRIVATE / f"training_EEV4_{arm}_seed{seed}.best.pt"


def latest_path(arm: str, seed: int) -> Path:
    return PRIVATE / f"training_EEV4_{arm}_seed{seed}.latest.pt"


def endpoint_path(arm: str, seed: int) -> Path:
    return PRIVATE / f"assessment_EEV4_{arm}_seed{seed}.finaleval.json"


def endpoint_users_path(arm: str, seed: int) -> Path:
    return PRIVATE / f"assessment_EEV4_{arm}_seed{seed}.finaleval.users.npz"


def endpoint_seal_path(arm: str, seed: int) -> Path:
    return PRIVATE / f"assessment_EEV4_{arm}_seed{seed}.finaleval.started.json"


READY = PRIVATE / "EEV4_FAMILY_READY.json"
STATUS = HERE / "ee_v4_status.json"
ADJUDICATION = HERE / "ee_v4_adjudication.json"


def frozen_config(arm: str, seed: int) -> dict[str, object]:
    return {
        "protocol": PROTOCOL,
        "repository_commit": repository_head(),
        "evidence_class": (
            "prospectively frozen outcome-known same-investigator comparator-fairness sensitivity"
        ),
        "upstream_url": UPSTREAM_URL,
        "upstream_commit": UPSTREAM_COMMIT,
        "upstream_source_sha256": UPSTREAM_SOURCE_HASHES,
        "data_sha256": {k: v for k, v in DATA_HASHES.items() if k != "test_data.df"},
        "test_free_full_history_sha256": TRAIN_VALID_INPUT_SHA256,
        "prior_public_adjudication_sha256": EEV3_ADJUDICATION_SHA256,
        "arm": arm,
        "model_type": MODEL_TYPES[arm],
        "seed": seed,
        "model_and_training": key_words(arm, seed),
        "max_epochs": MAX_EPOCHS,
        "patience": PATIENCE,
        "selection": (
            "maximum complete-history-masked full-catalog VALID NDCG@10; strict improvement"
        ),
        "inference": "cross-campaign descriptive independent-arm Welch",
        "test_read_or_scored": False,
    }


def validate_training_bundle(
    arm: str, seed: int, *, expected_commit: str | None = None
) -> dict[str, object]:
    path = training_path(arm, seed)
    checkpoint = best_path(arm, seed)
    if not path.is_file() or not checkpoint.is_file():
        raise RuntimeError(f"missing E-E V4 terminal bundle: {arm}/{seed}")
    obj = load_json(path)
    required = {
        "arm", "best_epoch", "best_valid", "checkpoint_file", "checkpoint_sha256",
        "config", "environment", "model_type", "protocol", "seed", "state",
        "stopped_epoch", "test_read_or_scored", "total_params",
        "trainable_params", "training_wall_seconds",
    }
    if set(obj) != required:
        raise RuntimeError(f"terminal schema drift: {arm}/{seed}")
    commit = expected_commit or repository_head()
    config = obj.get("config")
    if (obj["protocol"] != PROTOCOL or obj["state"] != "training_complete_test_unread"
            or obj["arm"] != arm or obj["seed"] != seed
            or obj["model_type"] != MODEL_TYPES[arm]
            or obj["test_read_or_scored"] is not False
            or obj["checkpoint_file"] != checkpoint.name
            or obj["checkpoint_sha256"] != sha256(checkpoint)
            or not isinstance(config, dict)
            or config.get("repository_commit") != commit
            or config.get("test_read_or_scored") is not False
            or config.get("model_and_training", {}).get("ID_embs_init_type") != "normal"
            or int(obj["best_epoch"]) < 0
            or int(obj["stopped_epoch"]) < int(obj["best_epoch"])
            or int(obj["total_params"]) <= 0 or int(obj["trainable_params"]) <= 0
            or not math.isfinite(float(obj["training_wall_seconds"]))
            or float(obj["training_wall_seconds"]) <= 0):
        raise RuntimeError(f"invalid E-E V4 terminal bundle: {arm}/{seed}")
    valid = obj["best_valid"]
    if not isinstance(valid, dict) or int(valid.get("n_eval", -1)) != N_USERS:
        raise RuntimeError(f"invalid E-E V4 VALID record: {arm}/{seed}")
    for name, value in valid.items():
        if name != "n_eval" and not isinstance(value, str) and not math.isfinite(float(value)):
            raise RuntimeError(f"non-finite VALID value {name}: {arm}/{seed}")
    return obj


def ready_payload(commit: str | None = None) -> dict[str, object]:
    commit = commit or repository_head()
    bundles = []
    for arm, seed in expected_pairs():
        train = validate_training_bundle(arm, seed, expected_commit=commit)
        bundles.append({
            "arm": arm,
            "seed": seed,
            "training_file": training_path(arm, seed).name,
            "training_sha256": sha256(training_path(arm, seed)),
            "checkpoint_file": best_path(arm, seed).name,
            "checkpoint_sha256": sha256(best_path(arm, seed)),
            "best_epoch": int(train["best_epoch"]),
        })
    return {
        "protocol": PROTOCOL,
        "state": "family_ready_test_unread",
        "repository_commit": commit,
        "arms": list(ARMS),
        "seeds": list(SEEDS),
        "n_training_bundles": len(bundles),
        "test_read_or_scored": False,
        "bundles": bundles,
    }
