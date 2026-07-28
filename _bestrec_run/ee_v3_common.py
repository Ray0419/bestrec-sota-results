#!/usr/bin/env python3
"""Shared frozen machinery for the clean AlphaFuse-style E-E V3 campaign."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch


ROOT = Path(__file__).resolve().parent.parent
HERE = ROOT / "_bestrec_run"
PRIVATE = HERE / "ee_v3_private"
UPSTREAM = ROOT / "ee_baselines" / "AlphaFuse"
DATA = ROOT / "ee_baselines" / "ours_DiT" / "data" / "ourdata" / "Video_Games"
INPUT_MANIFEST = HERE / "ee_v3_input_manifest.json"
TRAIN_VALID_INPUT = PRIVATE / "input" / "Video_Games.train_valid_full.npz"
PROTOCOL = "PREREG_EE_V3"
UPSTREAM_URL = "https://github.com/Hugo-Chinn/AlphaFuse.git"
UPSTREAM_COMMIT = "b501a0540b609370df995ad06fb245859b10a18a"
UPSTREAM_SOURCE_HASHES = {
    "models/backbone_SASRec.py": "4547ecb30e1a95fb9df8b404a495a61002df587f8e5fedff3df6f7bba51b0c19",
    "models/modules.py": "61cb6d35222a614cacaec069e358240945d210b454572afbc6eaf5ac7419599e",
    "train.py": "011309b730f5fe407890e7bd88f76d5e804da28ab07d03430343936ec4dc4c39",
    "utils.py": "dac859317ee4122309ede993453e697c5ab5c6b012304e2dc51abfeb578a39c2",
}
DATA_HASHES = {
    "train_data.df": "fa4323fa965b1f276486e24affdbb1ed0c9d4b4dec1d53ba6e87aef02cb7f5d2",
    "val_data.df": "3199456505feffeb2e2616bd5d8fcab436428c981e967b05a4c422636d62a824",
    "test_data.df": "5b44a116142d0c18e56ee256dfcb22bb33d3ed8b534988da811e991042b65964",
    "data_statis.df": "f4cda6b425a9d6dc7ce811d0374e71d1df453b8907d16efcdcddf7a092deec0e",
    "minilm_emb.pickle": "1bd2e941db2facb4a64e82178ce9a1eb91dd4763c771d6b355b758486acf44a1",
}
TRAIN_VALID_INPUT_SHA256 = "57d2011e0cc0af1cbbf9537b8c0352d8e53b5dc67a813cc81e4bf2836a002a3e"
ARMS = ("alphafuse_package", "sasrec_id")
MODEL_TYPES = {"alphafuse_package": "AlphaFuse", "sasrec_id": "SASRec"}
SEEDS = tuple(range(20262201, 20262209))
BOOTSTRAP_SEED = 20262299
N_BOOTSTRAP = 2000
N_USERS = 94762
N_ITEMS = 25612
MAX_LEN = 50
BATCH_SIZE = 256
MAX_EPOCHS = 500
PATIENCE = 50
REFERENCE_FILES = (
    "results_V2_ls02_filter8_VG.json",
    "results_V2_ls02_filter8_seed20260609_VG.json",
    "results_V2_ls02_filter8_seed20260610_VG.json",
    "results_V2_ls02_filter8_seed20260611_VG.json",
    "results_V2_ls02_filter8_seed20260612_VG.json",
    "results_V2_confirm_seed20260613_VG.json",
)
REFERENCE_RAW_SHA256 = {
    "results_V2_ls02_filter8_VG.json": "d391651bac4a2354054a4165f3df536a78e2604ad763d44bd0f509f6a588f1bd",
    "results_V2_ls02_filter8_seed20260609_VG.json": "737b2434cf1ce2cd1a01d646f06079b9a8644d34759a3929f331a2e82e63c183",
    "results_V2_ls02_filter8_seed20260610_VG.json": "db4f693bc37d5830569a69ea854dda19de74c505af9d5b59e560064e47c5d32f",
    "results_V2_ls02_filter8_seed20260611_VG.json": "f3a0032f76230fa9ab66e2c9e576856f13ad18930b480f9ef128073952ead3fa",
    "results_V2_ls02_filter8_seed20260612_VG.json": "ab2110f0c0973f65aba9359258528cf88a577a9f8bf549689e48778e02d3f422",
    "results_V2_confirm_seed20260613_VG.json": "d37cb83ba049b64bd2f5fdf694871d2d5948eccbbfb667b4cbfdc7ad3ac51c0b",
}
_VERIFIED_DATA: set[bool] = set()
_TRAIN_HISTORY_CACHE: tuple[list[list[int]], list[int]] | None = None
_EVAL_INPUT_CACHE: dict[str, tuple[list[list[int]], list[int], list[list[int]]]] = {}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def expected_pairs() -> tuple[tuple[str, int], ...]:
    return tuple((arm, seed) for arm in ARMS for seed in SEEDS)


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


def atomic_torch(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    torch.save(value, tmp)
    os.replace(tmp, path)


def atomic_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    os.replace(tmp, path)


def verify_file(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or sha256(path) != expected:
        raise RuntimeError(f"{label} identity mismatch: {path}")


def verify_upstream() -> None:
    if not (UPSTREAM / ".git").is_dir():
        raise RuntimeError("AlphaFuse checkout missing")
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=UPSTREAM, text=True, encoding="utf-8"
    ).strip()
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=UPSTREAM, text=True, encoding="utf-8"
    ).strip()
    if head != UPSTREAM_COMMIT or dirty:
        raise RuntimeError("AlphaFuse checkout is unpinned or tracked-dirty")
    for rel, expected in UPSTREAM_SOURCE_HASHES.items():
        verify_file(UPSTREAM / rel, expected, f"upstream {rel}")


def verify_data(*, include_test: bool) -> None:
    if include_test in _VERIFIED_DATA or (not include_test and True in _VERIFIED_DATA):
        return
    names = ["train_data.df", "val_data.df", "data_statis.df", "minilm_emb.pickle"]
    if include_test:
        names.append("test_data.df")
    for name in names:
        verify_file(DATA / name, DATA_HASHES[name], f"E-E V3 data {name}")
    verify_file(TRAIN_VALID_INPUT, TRAIN_VALID_INPUT_SHA256, "TEST-free full-history input")
    with INPUT_MANIFEST.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest != {
        "arrays": {"train_items": [625062], "train_offsets": [94763],
                   "user_index": [94762], "valid_target": [94762]},
        "contains_test_fields": False,
        "n_items": N_ITEMS,
        "n_train_interactions": 625062,
        "n_users": N_USERS,
        "private_input": "_bestrec_run/ee_v3_private/input/Video_Games.train_valid_full.npz",
        "private_input_sha256": TRAIN_VALID_INPUT_SHA256,
        "protocol": PROTOCOL,
        "source": "ee_baselines/export/Video_Games/Video_Games.sequences.jsonl",
        "source_sha256": "402fe06f0aa579f43162fbc15177f9f50a2241277a6b427c1ebf59cde8c72f5b",
    }:
        raise RuntimeError("E-E V3 input manifest drift")
    _VERIFIED_DATA.add(include_test)


def repository_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, encoding="utf-8"
    ).strip()


def load_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


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


def environment() -> dict[str, object]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "torch": torch.__version__,
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "cuda_runtime": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }


def key_words(arm: str, seed: int) -> dict[str, object]:
    if arm not in ARMS or seed not in SEEDS:
        raise RuntimeError("unknown E-E V3 arm/seed")
    return {
        "random_seed": seed, "lr": 0.001, "lr_delay_rate": 0.99,
        "lr_delay_epoch": 100, "epoch": MAX_EPOCHS, "data": "ourdata/Video_Games",
        "cuda": 0, "l2_decay": 1e-6, "batch_size": BATCH_SIZE,
        "num_blocks": 2, "num_heads": 1, "dropout_rate": 0.1,
        "loss_type": "infoNCE", "neg_ratio": 64, "temperature": 0.07,
        "beta": 0.1, "language_model_type": "minilm", "language_embs_scale": 40,
        "hidden_dim": 128, "ID_embs_init_type": "zeros",
        "model_type": MODEL_TYPES[arm], "SR_aligement_type": "con",
        "null_thres": None, "null_dim": 64, "item_frequency_flag": False,
        "standardization": True, "cover": False, "ID_space": "singular",
        "inject_space": "singular", "language_embs_path": str(DATA),
    }


def build_model(arm: str, seed: int, device: torch.device):
    verify_upstream()
    source = str(UPSTREAM)
    if source not in sys.path:
        sys.path.insert(0, source)
    from models.backbone_SASRec import AlphaFuse, SASRec
    cls = AlphaFuse if arm == "alphafuse_package" else SASRec
    return cls(device, **key_words(arm, seed)).to(device)


class SeqDataset(torch.utils.data.Dataset):
    def __init__(self, frame: pd.DataFrame):
        self.seq = [torch.tensor(x, dtype=torch.long) for x in frame["seq"]]
        self.target = [torch.tensor(int(x), dtype=torch.long) for x in frame["next"]]

    def __len__(self) -> int:
        return len(self.seq)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        return {"seq": self.seq[index], "next": self.target[index]}


def load_train_frame() -> pd.DataFrame:
    verify_data(include_test=False)
    frame = pd.read_pickle(DATA / "train_data.df").reset_index(drop=True)
    if len(frame) != 530300:
        raise RuntimeError("E-E V3 training row count mismatch")
    return frame


def load_train_histories() -> tuple[list[list[int]], list[int]]:
    global _TRAIN_HISTORY_CACHE
    if _TRAIN_HISTORY_CACHE is not None:
        return _TRAIN_HISTORY_CACHE
    verify_data(include_test=False)
    with np.load(TRAIN_VALID_INPUT, allow_pickle=False) as z:
        users = z["user_index"]
        offsets = z["train_offsets"]
        items = z["train_items"]
        valid = z["valid_target"]
    if (users.tolist() != list(range(N_USERS)) or len(offsets) != N_USERS + 1
            or offsets[0] != 0 or offsets[-1] != len(items)
            or np.any(np.diff(offsets) <= 0) or len(valid) != N_USERS):
        raise RuntimeError("E-E V3 full-history structure mismatch")
    histories = [items[offsets[i]:offsets[i + 1]].astype(np.int64).tolist()
                 for i in range(N_USERS)]
    _TRAIN_HISTORY_CACHE = (histories, valid.astype(np.int64).tolist())
    return _TRAIN_HISTORY_CACHE


def load_eval_inputs(split: str) -> tuple[list[list[int]], list[int], list[list[int]]]:
    if split not in {"valid", "test"}:
        raise RuntimeError("unknown split")
    if split in _EVAL_INPUT_CACHE:
        return _EVAL_INPUT_CACHE[split]
    verify_data(include_test=(split == "test"))
    train_histories, valid_targets = load_train_histories()
    name = "val_data.df" if split == "valid" else "test_data.df"
    frame = pd.read_pickle(DATA / name).reset_index(drop=True)
    if len(frame) != N_USERS:
        raise RuntimeError(f"E-E V3 {split} row count mismatch")
    seqs = [[int(x) for x in row] for row in frame["seq"]]
    targets = [int(x) for x in frame["next"]]
    expected_targets = valid_targets if split == "valid" else targets
    if split == "valid" and targets != expected_targets:
        raise RuntimeError("E-E V3 VALID target/order mismatch")
    seen = (train_histories if split == "valid" else
            [history + [valid_targets[i]] for i, history in enumerate(train_histories)])
    for i, seq in enumerate(seqs):
        if len(seq) != MAX_LEN or any(x < 0 or x > N_ITEMS for x in seq):
            raise RuntimeError(f"E-E V3 {split} model-input schema mismatch")
        history_for_input = (train_histories[i] if split == "valid" else
                             train_histories[i] + [valid_targets[i]])
        tail = history_for_input[-MAX_LEN:]
        expected_seq = [N_ITEMS] * (MAX_LEN - len(tail)) + tail
        if seq != expected_seq:
            raise RuntimeError(f"E-E V3 {split} user/order/model-input mismatch at {i}")
    _EVAL_INPUT_CACHE[split] = (seqs, targets, seen)
    return _EVAL_INPUT_CACHE[split]


def ranks_from_scores(scores: np.ndarray, targets: list[int], seen: list[list[int]]) -> np.ndarray:
    values = np.asarray(scores, dtype=np.float64).copy()
    if values.ndim != 2 or values.shape[0] != len(targets) or values.shape[1] != N_ITEMS:
        raise RuntimeError("E-E V3 score matrix shape mismatch")
    for row, history in enumerate(seen):
        target = int(targets[row])
        if not (0 <= target < N_ITEMS):
            raise RuntimeError("E-E V3 target range mismatch")
        idx = np.asarray([int(x) for x in history if int(x) != target], dtype=np.int64)
        if idx.size:
            values[row, idx] = -np.inf
    target_scores = values[np.arange(len(targets)), np.asarray(targets, dtype=np.int64)]
    if not np.isfinite(target_scores).all():
        raise RuntimeError("E-E V3 target masked/nonfinite")
    return (values > target_scores[:, None]).sum(axis=1).astype(np.int64)


def metric_family(rank0: np.ndarray) -> dict[str, float | int]:
    r = np.asarray(rank0, dtype=np.int64)
    if r.ndim != 1 or len(r) == 0 or r.min() < 0 or r.max() >= N_ITEMS:
        raise RuntimeError("E-E V3 invalid rank vector")
    out: dict[str, float | int] = {"n_eval": int(len(r))}
    for cutoff in (5, 10, 20, 50):
        hit = r < cutoff
        out[f"HR@{cutoff}"] = float(hit.mean())
        out[f"NDCG@{cutoff}"] = float(np.where(
            hit, 1.0 / np.log2(r.astype(np.float64) + 2.0), 0.0).mean())
        out[f"MRR@{cutoff}"] = float(np.where(
            hit, 1.0 / (r.astype(np.float64) + 1.0), 0.0).mean())
    out["MRR"] = float((1.0 / (r.astype(np.float64) + 1.0)).mean())
    return out


def evaluate_model(model, split: str, device: torch.device, *, keep_records: bool,
                   profile: bool = False) -> tuple[dict[str, object], dict[str, np.ndarray] | None]:
    seqs, targets, seen = load_eval_inputs(split)
    model.eval()
    all_ranks: list[np.ndarray] = []
    started = time.perf_counter()
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    with torch.no_grad():
        item_mat = model.return_item_emb()[:-1]
        for start in range(0, N_USERS, 256):
            stop = min(start + 256, N_USERS)
            seq = torch.tensor(seqs[start:stop], dtype=torch.long, device=device)
            state = model.forward(seq)
            if state.dim() == 1:
                state = state.unsqueeze(0)
            scores = (state @ item_mat.t()).float().cpu().numpy()
            all_ranks.append(ranks_from_scores(scores, targets[start:stop], seen[start:stop]))
    elapsed = time.perf_counter() - started
    ranks = np.concatenate(all_ranks)
    metrics: dict[str, object] = metric_family(ranks)
    metrics.update({
        "eval_seconds": float(elapsed),
        "users_per_second": float(N_USERS / elapsed),
        "cuda_peak_allocated_bytes": (int(torch.cuda.max_memory_allocated(device))
                                       if device.type == "cuda" else 0),
    })
    if profile:
        probe_n = 64
        seq = torch.tensor(seqs[:probe_n], dtype=torch.long, device=device)
        activities = [torch.profiler.ProfilerActivity.CPU]
        if device.type == "cuda":
            activities.append(torch.profiler.ProfilerActivity.CUDA)
        with torch.no_grad(), torch.profiler.profile(activities=activities, with_flops=True) as prof:
            state = model.forward(seq)
            _ = state @ model.return_item_emb()[:-1].t()
            if device.type == "cuda":
                torch.cuda.synchronize(device)
        flops = sum(int(getattr(evt, "flops", 0) or 0) for evt in prof.key_averages())
        metrics["profiler_probe_users"] = probe_n
        metrics["profiler_accounted_flops_total"] = int(flops)
        metrics["profiler_accounted_flops_per_user"] = float(flops / probe_n)
        metrics["profiler_scope"] = "model forward plus full-catalog item-score matmul; operator-accounted lower bound"
    records = None
    if keep_records:
        rr = 1.0 / (ranks.astype(np.float64) + 1.0)
        hit10 = ranks < 10
        records = {
            "user_index": np.arange(N_USERS, dtype=np.int64),
            "target_item_id": np.asarray(targets, dtype=np.int64),
            "rank0": ranks,
            "ndcg10": np.where(hit10, 1.0 / np.log2(ranks.astype(np.float64) + 2.0), 0.0),
            "hr10": hit10.astype(np.int8),
            "rr": rr,
        }
    return metrics, records


def training_path(arm: str, seed: int) -> Path:
    return PRIVATE / f"training_EEV3_{arm}_seed{seed}.json"


def started_path(arm: str, seed: int) -> Path:
    return PRIVATE / f"training_EEV3_{arm}_seed{seed}.started.json"


def best_path(arm: str, seed: int) -> Path:
    return PRIVATE / f"training_EEV3_{arm}_seed{seed}.best.pt"


def latest_path(arm: str, seed: int) -> Path:
    return PRIVATE / f"training_EEV3_{arm}_seed{seed}.latest.pt"


def endpoint_path(arm: str, seed: int) -> Path:
    return PRIVATE / f"assessment_EEV3_{arm}_seed{seed}.finaleval.json"


def endpoint_users_path(arm: str, seed: int) -> Path:
    return PRIVATE / f"assessment_EEV3_{arm}_seed{seed}.finaleval.users.npz"


def endpoint_seal_path(arm: str, seed: int) -> Path:
    return PRIVATE / f"assessment_EEV3_{arm}_seed{seed}.finaleval.started.json"


READY = PRIVATE / "EEV3_FAMILY_READY.json"
STATUS = HERE / "ee_v3_status.json"
ADJUDICATION = HERE / "ee_v3_adjudication.json"


def frozen_config(arm: str, seed: int) -> dict[str, object]:
    return {
        "protocol": PROTOCOL,
        "repository_commit": repository_head(),
        "evidence_class": "prospectively frozen execution on an outcome-known split by the same investigators",
        "upstream_url": UPSTREAM_URL,
        "upstream_commit": UPSTREAM_COMMIT,
        "upstream_source_sha256": UPSTREAM_SOURCE_HASHES,
        "data_sha256": {k: v for k, v in DATA_HASHES.items() if k != "test_data.df"},
        "test_free_full_history_sha256": TRAIN_VALID_INPUT_SHA256,
        "arm": arm,
        "model_type": MODEL_TYPES[arm],
        "seed": seed,
        "model_and_training": key_words(arm, seed),
        "max_epochs": MAX_EPOCHS,
        "patience": PATIENCE,
        "selection": "maximum complete-history-masked full-catalog VALID NDCG@10; strict improvement",
        "inference": "independent-arm Welch; same-number seeds are labels, not pairing",
        "test_read_or_scored": False,
    }


def validate_training_bundle(arm: str, seed: int, *, expected_commit: str | None = None) -> dict[str, object]:
    path = training_path(arm, seed)
    checkpoint = best_path(arm, seed)
    if not path.is_file() or not checkpoint.is_file():
        raise RuntimeError(f"missing E-E V3 terminal bundle: {arm}/{seed}")
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
    if (obj["protocol"] != PROTOCOL or obj["state"] != "training_complete_test_unread"
            or obj["arm"] != arm or obj["seed"] != seed
            or obj["model_type"] != MODEL_TYPES[arm]
            or obj["test_read_or_scored"] is not False
            or obj["checkpoint_file"] != checkpoint.name
            or obj["checkpoint_sha256"] != sha256(checkpoint)
            or not isinstance(obj["config"], dict)
            or obj["config"].get("repository_commit") != commit
            or obj["config"].get("test_read_or_scored") is not False
            or int(obj["best_epoch"]) < 0
            or int(obj["stopped_epoch"]) < int(obj["best_epoch"])
            or int(obj["total_params"]) <= 0 or int(obj["trainable_params"]) <= 0
            or not math.isfinite(float(obj["training_wall_seconds"]))
            or float(obj["training_wall_seconds"]) <= 0):
        raise RuntimeError(f"invalid E-E V3 terminal bundle: {arm}/{seed}")
    valid = obj["best_valid"]
    if not isinstance(valid, dict) or int(valid.get("n_eval", -1)) != N_USERS:
        raise RuntimeError(f"invalid E-E V3 VALID record: {arm}/{seed}")
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
