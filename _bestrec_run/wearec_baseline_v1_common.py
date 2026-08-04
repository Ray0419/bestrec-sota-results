#!/usr/bin/env python3
"""Shared frozen machinery for the official WEARec V1 comparator phase."""

from __future__ import annotations

import bisect
import csv
import hashlib
import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset


ROOT = Path(__file__).resolve().parent.parent
HERE = ROOT / "_bestrec_run"
PRIVATE = HERE / "wearec_baseline_v1_private"
UPSTREAM = ROOT / "ee_baselines" / "WEARec"
CATALOG = PRIVATE / "catalog.json"
CATALOG_MANIFEST = HERE / "wearec_baseline_v1_catalog_manifest.json"
SPLIT_DIR = ROOT / "data_5core" / "5core" / "last_out"
PROTOCOL = "PREREG_WEAREC_BASELINE_V1"
UPSTREAM_URL = "https://github.com/xhy963319431/WEARec.git"
UPSTREAM_COMMIT = "2087335339b1ead87da6e066ce14e2d33880a95e"
CATALOG_SHA256 = "461a8e541da3f528d7ed768339e319b0bfdb1f243c1f29400f5edbd8c017f31a"
SPLIT_HASHES = {
    "train": "536866c7b3cb21ff4a1c2139ecb1e393c2ea468c4efe63ff1cfde51b0bcaa8d3",
    "valid": "b70d195ab3b9f76082854671e0e6a94c444302db6169d4074f112695d1467711",
    "test": "5a21bbcb5106d48cca21e90bbb6c417e1b95ac406321cd300c7800759dbaa496",
}
UPSTREAM_SOURCE_HASHES = {
    "src/model/__init__.py": "8cf81baaa0626586caa130fe6b6f5269e5afa18a8269509bc520e36ef947afa4",
    "src/model/wearec.py": "77d9012dfed909db88fff824d0a2126b921ab234029943a2172bb4b0c77f3d01",
    "src/model/_abstract_model.py": "525a86904354c6a6acb513a0d93cffdd44e9e4bde4dcc39fb4cc04a0c9dbc544",
    "src/model/_modules.py": "11c34e5cc094e4b903f9779e878fcbd5c7cf687b23a24f161ccdd174ad8a1d0c",
}
PRESETS = {
    # Exact Amazon-domain configurations distributed in the official checkout.
    "official_sports": {"lr": 0.001, "dropout": 0.5, "alpha": 0.3, "num_heads": 4},
    "official_beauty": {"lr": 0.0005, "dropout": 0.5, "alpha": 0.2, "num_heads": 8},
}
PRESET_ORDER = ("official_sports", "official_beauty")
TUNE_SEED = 20262000
ASSESSMENT_SEEDS = tuple(range(20262001, 20262009))
MAX_LEN = 50
BATCH_SIZE = 256
MAX_EPOCHS = 200
PATIENCE = 10
N_EXPECTED_USERS = 94762
N_EXPECTED_ITEMS = 25612


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    os.replace(tmp, path)


def exclusive_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")


def verify_file(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or sha256(path) != expected:
        raise RuntimeError(f"{label} identity mismatch: {path}")


def verify_upstream() -> None:
    if not (UPSTREAM / ".git").is_dir():
        raise RuntimeError("official WEARec checkout missing; run acquire_wearec_baseline_v1.py")
    import subprocess

    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=UPSTREAM, text=True, encoding="utf-8"
    ).strip()
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=UPSTREAM,
        text=True,
        encoding="utf-8",
    ).strip()
    if head != UPSTREAM_COMMIT or dirty:
        raise RuntimeError("official WEARec checkout is unpinned or dirty")
    for rel, expected in UPSTREAM_SOURCE_HASHES.items():
        verify_file(UPSTREAM / rel, expected, f"upstream {rel}")


def repository_head() -> str:
    import subprocess

    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, encoding="utf-8"
    ).strip()


def load_catalog() -> tuple[list[str], dict[str, int]]:
    verify_file(CATALOG, CATALOG_SHA256, "private catalog")
    with CATALOG.open("r", encoding="utf-8") as handle:
        obj = json.load(handle)
    if obj.get("protocol") != PROTOCOL or len(obj.get("items", [])) != N_EXPECTED_ITEMS:
        raise RuntimeError("private catalog schema/count mismatch")
    items = obj["items"]
    if items != sorted(items) or len(items) != len(set(items)):
        raise RuntimeError("private catalog is not a unique lexicographic list")
    return items, {item: index + 1 for index, item in enumerate(items)}


def split_path(split: str) -> Path:
    return SPLIT_DIR / f"Video_Games.{split}.csv"


def verify_split(split: str) -> Path:
    path = split_path(split)
    verify_file(path, SPLIT_HASHES[split], f"{split} split")
    return path


def set_seed(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)


@dataclass
class DataBundle:
    user_names: list[str]
    train_sequences: list[list[int]]
    valid_targets: list[int]
    n_items: int


def _read_rows(path: Path) -> Iterable[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        yield from csv.DictReader(handle)


def load_train_valid(item_to_id: dict[str, int]) -> DataBundle:
    # Deliberately no TEST path is referenced in this function.
    train_path = verify_split("train")
    valid_path = verify_split("valid")
    by_user: dict[str, list[tuple[int, int]]] = {}
    for row in _read_rows(train_path):
        try:
            item = item_to_id[row["parent_asin"]]
        except KeyError as exc:
            raise RuntimeError("TRAIN item absent from frozen catalog") from exc
        by_user.setdefault(row["user_id"], []).append((int(row["timestamp"]), item))
    users = sorted(by_user)
    if len(users) != N_EXPECTED_USERS:
        raise RuntimeError(f"TRAIN user count mismatch: {len(users)}")
    index = {user: pos for pos, user in enumerate(users)}
    sequences: list[list[int]] = []
    for user in users:
        ordered = sorted(by_user[user], key=lambda value: (value[0], value[1]))
        sequences.append([item for _, item in ordered])
    valid_targets = [0] * len(users)
    seen_valid: set[int] = set()
    for row in _read_rows(valid_path):
        if row["user_id"] not in index or row["parent_asin"] not in item_to_id:
            raise RuntimeError("VALID identity absent from frozen TRAIN/catalog map")
        pos = index[row["user_id"]]
        if pos in seen_valid:
            raise RuntimeError("VALID contains multiple rows for one user")
        seen_valid.add(pos)
        valid_targets[pos] = item_to_id[row["parent_asin"]]
    if len(seen_valid) != len(users) or any(target == 0 for target in valid_targets):
        raise RuntimeError("VALID is not exactly one target per TRAIN user")
    return DataBundle(users, sequences, valid_targets, len(item_to_id))


def load_test_targets(bundle: DataBundle, item_to_id: dict[str, int]) -> list[int]:
    test_path = verify_split("test")
    index = {user: pos for pos, user in enumerate(bundle.user_names)}
    targets = [0] * len(bundle.user_names)
    seen: set[int] = set()
    for row in _read_rows(test_path):
        if row["user_id"] not in index or row["parent_asin"] not in item_to_id:
            raise RuntimeError("TEST identity absent from frozen user/catalog map")
        pos = index[row["user_id"]]
        if pos in seen:
            raise RuntimeError("TEST contains multiple rows for one user")
        seen.add(pos)
        targets[pos] = item_to_id[row["parent_asin"]]
    if len(seen) != len(targets) or any(target == 0 for target in targets):
        raise RuntimeError("TEST is not exactly one target per user")
    return targets


class PrefixTrainDataset(Dataset):
    """Official WEARec's last-50 training-prefix construction, without TEST reads."""

    def __init__(self, sequences: list[list[int]]):
        self.sequences = [sequence[-MAX_LEN:] for sequence in sequences]
        lengths = np.asarray([len(sequence) for sequence in self.sequences], dtype=np.int64)
        if (lengths <= 0).any():
            raise RuntimeError("empty TRAIN sequence")
        self.cumulative = np.cumsum(lengths)

    def __len__(self) -> int:
        return int(self.cumulative[-1])

    def __getitem__(self, index: int):
        user = bisect.bisect_right(self.cumulative, index)
        prior = 0 if user == 0 else int(self.cumulative[user - 1])
        prefix_len = index - prior + 1
        sequence = self.sequences[user]
        answer = sequence[prefix_len - 1]
        history = sequence[: prefix_len - 1]
        padded = [0] * (MAX_LEN - len(history)) + history
        return (
            torch.tensor(user, dtype=torch.long),
            torch.tensor(padded, dtype=torch.long),
            torch.tensor(answer, dtype=torch.long),
        )


def model_args(preset: str, n_items: int) -> SimpleNamespace:
    if preset not in PRESETS:
        raise RuntimeError(f"unknown frozen preset: {preset}")
    cfg = PRESETS[preset]
    return SimpleNamespace(
        item_size=n_items + 1,
        num_users=N_EXPECTED_USERS + 1,
        batch_size=BATCH_SIZE,
        max_seq_length=MAX_LEN,
        hidden_size=64,
        num_hidden_layers=2,
        hidden_act="gelu",
        num_attention_heads=2,
        attention_probs_dropout_prob=cfg["dropout"],
        hidden_dropout_prob=cfg["dropout"],
        initializer_range=0.02,
        num_heads=cfg["num_heads"],
        alpha=cfg["alpha"],
        no_cuda=False,
    )


def build_model(preset: str, n_items: int):
    verify_upstream()
    src = str(UPSTREAM / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from model.wearec import WEARecModel

    return WEARecModel(model_args(preset, n_items))


def padded_inputs(histories: list[list[int]], device: torch.device) -> torch.Tensor:
    array = np.zeros((len(histories), MAX_LEN), dtype=np.int64)
    for row, history in enumerate(histories):
        truncated = history[-MAX_LEN:]
        if truncated:
            array[row, MAX_LEN - len(truncated) :] = truncated
    return torch.from_numpy(array).to(device)


def evaluate(
    model,
    histories: list[list[int]],
    targets: list[int],
    n_items: int,
    device: torch.device,
    *,
    keep_records: bool,
) -> tuple[dict[str, float | int], dict[str, np.ndarray] | None]:
    if len(histories) != len(targets):
        raise RuntimeError("history/target length mismatch")
    model.eval()
    ranks: list[np.ndarray] = []
    started = time.perf_counter()
    with torch.no_grad():
        item_embeddings = model.item_embeddings.weight
        for start in range(0, len(targets), 512):
            stop = min(start + 512, len(targets))
            batch_histories = histories[start:stop]
            input_ids = padded_inputs(batch_histories, device)
            hidden = model.predict(input_ids, None)[:, -1, :]
            scores = hidden @ item_embeddings.transpose(0, 1)
            scores[:, 0] = -torch.inf
            for row, history in enumerate(batch_histories):
                if history:
                    scores[row, torch.tensor(history, dtype=torch.long, device=device)] = -torch.inf
            target_tensor = torch.tensor(targets[start:stop], dtype=torch.long, device=device)
            target_scores = scores[torch.arange(stop - start, device=device), target_tensor]
            rank = (scores > target_scores.unsqueeze(1)).sum(dim=1).cpu().numpy().astype(np.int64)
            ranks.append(rank)
    rank0 = np.concatenate(ranks)
    hit = rank0 < 10
    ndcg = np.where(hit, 1.0 / np.log2(rank0.astype(np.float64) + 2.0), 0.0)
    rr = 1.0 / (rank0.astype(np.float64) + 1.0)
    summary: dict[str, float | int] = {
        "NDCG@10": float(ndcg.mean()),
        "HR@10": float(hit.mean()),
        "MRR": float(rr.mean()),
        "n_eval": int(len(rank0)),
        "eval_seconds": float(time.perf_counter() - started),
    }
    records = None
    if keep_records:
        records = {
            "user_index": np.arange(len(rank0), dtype=np.int64),
            "target_item_id": np.asarray(targets, dtype=np.int64),
            "rank0": rank0,
            "ndcg10": ndcg,
            "hr10": hit.astype(np.int8),
            "rr": rr,
        }
    return summary, records


def train_output(phase: str, preset: str, seed: int) -> Path:
    return PRIVATE / f"{phase}_WEAREC_V1_{preset}_seed{seed}.json"


def checkpoint_path(phase: str, preset: str, seed: int) -> Path:
    return PRIVATE / f"{phase}_WEAREC_V1_{preset}_seed{seed}.best.pt"


def endpoint_path(preset: str, seed: int) -> Path:
    return PRIVATE / f"assessment_WEAREC_V1_{preset}_seed{seed}.finaleval.json"


def endpoint_users_path(preset: str, seed: int) -> Path:
    return PRIVATE / f"assessment_WEAREC_V1_{preset}_seed{seed}.finaleval.users.npz"


def endpoint_seal_path(preset: str, seed: int) -> Path:
    return PRIVATE / f"assessment_WEAREC_V1_{preset}_seed{seed}.finaleval.started.json"


def checkpoint_payload(model, preset: str, seed: int, best_epoch: int, best_valid: float) -> dict:
    return {
        "protocol": PROTOCOL,
        "upstream_commit": UPSTREAM_COMMIT,
        "preset": preset,
        "seed": seed,
        "best_epoch": best_epoch,
        "best_valid_ndcg10": best_valid,
        "state_dict": model.state_dict(),
    }


def frozen_config(preset: str, seed: int, phase: str) -> dict:
    return {
        "protocol": PROTOCOL,
        "repository_commit": repository_head(),
        "phase": phase,
        "model": "official WEARec",
        "upstream_url": UPSTREAM_URL,
        "upstream_commit": UPSTREAM_COMMIT,
        "upstream_source_sha256": UPSTREAM_SOURCE_HASHES,
        "dataset": "Amazon Reviews 2023 Video_Games 5-core LLOO",
        "split_sha256": {"train": SPLIT_HASHES["train"], "valid": SPLIT_HASHES["valid"]},
        "private_catalog_sha256": CATALOG_SHA256,
        "catalog_policy": "prefrozen all-split identity map; trainer reads TRAIN+VALID only",
        "preset": preset,
        "preset_values": PRESETS[preset],
        "seed": seed,
        "max_seq_length": MAX_LEN,
        "hidden_size": 64,
        "num_hidden_layers": 2,
        "batch_size": BATCH_SIZE,
        "max_epochs": MAX_EPOCHS,
        "patience": PATIENCE,
        "optimizer": "Adam(beta1=0.9,beta2=0.999,weight_decay=0)",
        "loss": "official full-catalog cross entropy including padding class",
        "selection": "maximum shared-evaluator VALID NDCG@10; strict improvement",
        "test_read_or_scored": False,
    }
