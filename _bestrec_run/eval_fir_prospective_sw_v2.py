#!/usr/bin/env python3
"""Outcome-silent one-shot TEST evaluator for prospective Software FIR V2."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import subprocess
import time
from pathlib import Path

import numpy as np
import torch

import fuse_ease_eval as fee
import run_fir_prospective_sw_v2 as campaign
import run_sasrec_sbert_pointwise_v1_frozen as rsp


PROTOCOL = campaign.PROTOCOL


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("x", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=2, allow_nan=False)
        fh.write("\n")
    os.replace(tmp, path)


def current_head() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=campaign.ROOT,
                            capture_output=True, text=True, check=True)
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_json")
    args = parser.parse_args()
    run_path = Path(args.run_json).resolve()
    if run_path not in {campaign.path_for(arm, seed).resolve()
                        for seed in campaign.SEEDS for arm in campaign.ARMS}:
        raise RuntimeError("run path is outside the frozen campaign")
    ckpt_path = run_path.with_suffix(".best.pt")
    out_path = run_path.with_suffix(".finaleval.json")
    users_path = run_path.with_suffix(".finaleval.users.npz")
    seal_path = run_path.with_suffix(".finaleval.started.json")
    if not run_path.is_file() or not ckpt_path.is_file():
        raise RuntimeError("missing run JSON or checkpoint")
    if out_path.exists() or users_path.exists() or seal_path.exists():
        raise RuntimeError("refusing repeat TEST access")
    if not campaign.all_training_ready():
        raise RuntimeError("all 16 training runs must finish before first TEST access")

    base = json.loads(run_path.read_text(encoding="utf-8"))
    cfg = base["config"]
    custody = base.get("prospective_custody", {})
    arm = cfg.get("fir_control")
    if (cfg.get("category") != campaign.CATEGORY or arm not in campaign.ARMS
            or cfg.get("fir_control_kernel") != campaign.KERNEL
            or not cfg.get("no_test_eval") or not cfg.get("save_ckpt")
            or base.get("best_test") is not None
            or any("test" in epoch for epoch in base.get("history", []))
            or custody.get("protocol") != PROTOCOL
            or custody.get("execution_git_head") != current_head()):
        raise RuntimeError("run violates frozen training/custody boundary")
    for seed in campaign.SEEDS:
        for candidate_arm in campaign.ARMS:
            campaign.validate_training_json(
                campaign.path_for(candidate_arm, seed), candidate_arm, seed,
                custody["execution_git_head"])
    for rel, expected in campaign.EXPECTED_INPUT_SHA256.items():
        if sha256(campaign.ROOT / rel) != expected:
            raise RuntimeError(f"frozen input mismatch before TEST: {rel}")

    seal = {
        "protocol": PROTOCOL,
        "started_unix": time.time(),
        "execution_git_head": custody["execution_git_head"],
        "run_json": run_path.name,
        "run_json_sha256": sha256(run_path),
        "checkpoint": ckpt_path.name,
        "checkpoint_sha256": sha256(ckpt_path),
    }
    fd = os.open(seal_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(seal, fh, indent=2)
        fh.write("\n")

    train_file = rsp.SPLIT_DIR / "Software.train.csv"
    valid_file = rsp.SPLIT_DIR / "Software.valid.csv"
    test_file = rsp.SPLIT_DIR / "Software.test.csv"
    train_rows = rsp.load_split_csv(train_file)
    valid_rows = rsp.load_split_csv(valid_file)
    test_rows = rsp.load_split_csv(test_file)
    train, valid, test, _, items = rsp.reindex(train_rows, valid_rows, test_rows)
    n_items, pad_id = len(items), len(items)
    seqs = rsp.build_user_sequences(train)
    times = rsp.build_user_time_sequences(train) if cfg.get("time_bias") else None
    val_extra, val_times = {}, {}
    for user, item, _, timestamp in valid:
        val_extra.setdefault(user, []).append(item)
        val_times.setdefault(user, []).append(timestamp // 1000)
    emb_path = campaign.ROOT / "cache_5core" / "sbert_titles_Software.npy"
    sbert = np.load(emb_path).astype(np.float32)
    if sbert.shape != (n_items, 384):
        raise RuntimeError(f"title-cache shape mismatch: {sbert.shape} != {(n_items, 384)}")

    checkpoint = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    proto = [value.to(rsp.DEVICE) for value in checkpoint.get("proto_assign", [])] or None
    fee.rsp = rsp
    model = fee.build_model_from_config(cfg, n_items, pad_id, sbert, proto)
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    model.to(rsp.DEVICE).eval()
    with contextlib.redirect_stdout(io.StringIO()):
        metrics = rsp.evaluate(
            model, seqs, test, n_items, pad_id, cfg["max_seq_len"],
            rsp.DEVICE, top_k=10, batch_size=512,
            extra_history=val_extra, user_times=times, extra_times=val_times,
            cosine=cfg.get("cosine_scoring", False))
    records = metrics.pop("_user_records")
    tmp_users = users_path.with_suffix(users_path.suffix + ".tmp")
    with tmp_users.open("xb") as fh:
        np.savez_compressed(fh, **{key: np.asarray(value) for key, value in records.items()})
    os.replace(tmp_users, users_path)

    artifact = {
        "protocol": PROTOCOL,
        "category": campaign.CATEGORY,
        "seed": cfg["seed"],
        "arm": arm,
        "selected_epoch": int(checkpoint["epoch"]),
        "selected_val_NDCG10": float(checkpoint["val_NDCG10"]),
        "test": metrics,
        "provenance": {
            **seal,
            "started_seal_sha256": sha256(seal_path),
            "base_trainer_sha256_lf": sha256_lf(Path(rsp.__file__)),
            "evaluator_sha256_lf": sha256_lf(Path(__file__)),
            "train_split_sha256": sha256(train_file),
            "valid_split_sha256": sha256(valid_file),
            "test_split_sha256": sha256(test_file),
            "title_cache_sha256": sha256(emb_path),
            "users_sidecar": users_path.name,
            "users_sidecar_sha256": sha256(users_path),
        },
    }
    atomic_json(out_path, artifact)
    print(f"sealed final-evaluation artifact written: {out_path.name}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"INTEGRITY FAIL: {exc}")
        raise SystemExit(2)
