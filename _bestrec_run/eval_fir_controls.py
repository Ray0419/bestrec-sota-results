# -*- coding: utf-8 -*-
"""One-shot, outcome-silent TEST evaluator for PREREG_FIR_CONTROLS.

The training run must have used --no-test-eval --save-ckpt.  This program
creates an exclusive STARTED seal before touching TEST and refuses to rerun.
It writes metrics and per-user records without printing any endpoint value;
the committed adjudicator is the first reader of those artifacts.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import time
from pathlib import Path

import numpy as np
import torch

import run_sasrec_sbert as rsp
from fuse_ease_eval import build_model_from_config


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_json")
    args = ap.parse_args()
    run_path = Path(args.run_json).resolve()
    ckpt_path = run_path.with_suffix(".best.pt")
    out_path = run_path.with_suffix(".finaleval.json")
    users_path = run_path.with_suffix(".finaleval.users.npz")
    seal_path = run_path.with_suffix(".finaleval.started.json")
    for p in (run_path, ckpt_path):
        if not p.exists():
            raise SystemExit(f"missing required artifact: {p}")
    if out_path.exists() or users_path.exists() or seal_path.exists():
        raise SystemExit("refusing repeat TEST access: final artifact or STARTED seal exists")

    base = json.load(open(run_path, encoding="utf-8"))
    cfg = base["config"]
    if not cfg.get("no_test_eval") or not cfg.get("save_ckpt"):
        raise SystemExit("run was not trained with --no-test-eval --save-ckpt")
    if base.get("best_test") is not None or any("test" in x for x in base["history"]):
        raise SystemExit("TEST was not sequestered during training")

    # O_EXCL makes the one-shot boundary fail closed even under two processes.
    seal = {
        "protocol": "PREREG_FIR_CONTROLS",
        "started_unix": time.time(),
        "run_json": run_path.name,
        "run_json_sha256": sha256(run_path),
        "checkpoint": ckpt_path.name,
        "checkpoint_sha256": sha256(ckpt_path),
    }
    fd = os.open(seal_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(seal, f, indent=2)

    category = cfg["category"]
    train_file = rsp.SPLIT_DIR / f"{category}.train.csv"
    valid_file = rsp.SPLIT_DIR / f"{category}.valid.csv"
    test_file = rsp.SPLIT_DIR / f"{category}.test.csv"
    train_rows = rsp.load_split_csv(train_file)
    valid_rows = rsp.load_split_csv(valid_file)
    test_rows = rsp.load_split_csv(test_file)
    train, valid, test, _, items = rsp.reindex(train_rows, valid_rows, test_rows)
    n_items, pad_id = len(items), len(items)
    seqs = rsp.build_user_sequences(train)
    times = rsp.build_user_time_sequences(train) if cfg.get("time_bias") else None
    val_extra, val_times = {}, {}
    for u, i, _, t in valid:
        val_extra.setdefault(u, []).append(i)
        val_times.setdefault(u, []).append(t // 1000)

    cache = cfg.get("encoder_cache")
    emb_path = Path(cache) if cache else rsp.EMB_CACHE_DIR / f"sbert_titles_{category}.npy"
    sbert = None if cfg.get("no_sbert") else np.load(emb_path).astype(np.float32)[:n_items]
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    proto = [x.to(rsp.DEVICE) for x in ckpt.get("proto_assign", [])] or None
    model = build_model_from_config(cfg, n_items, pad_id, sbert, proto)
    model.load_state_dict(ckpt["state_dict"], strict=True)
    model.to(rsp.DEVICE).eval()

    # Suppress all progress and stratified metric prints: no outcome is exposed
    # until adjudication reads the sealed artifacts.
    with contextlib.redirect_stdout(io.StringIO()):
        metrics = rsp.evaluate(
            model, seqs, test, n_items, pad_id, cfg["max_seq_len"],
            rsp.DEVICE, top_k=10, batch_size=512,
            extra_history=val_extra, user_times=times, extra_times=val_times,
            cosine=cfg.get("cosine_scoring", False))
    records = metrics.pop("_user_records")
    tmp_users = users_path.with_suffix(users_path.suffix + ".tmp")
    with open(tmp_users, "wb") as f:
        np.savez_compressed(f, **{k: np.asarray(v) for k, v in records.items()})
    os.replace(tmp_users, users_path)

    artifact = {
        "protocol": "PREREG_FIR_CONTROLS",
        "category": category,
        "seed": cfg["seed"],
        "arm": cfg["fir_control"],
        "selected_epoch": int(ckpt["epoch"]),
        "selected_val_NDCG10": float(ckpt["val_NDCG10"]),
        "test": metrics,
        "provenance": {
            **seal,
            "started_seal_sha256": sha256(seal_path),
            "trainer_sha256": sha256(Path(rsp.__file__)),
            "evaluator_sha256": sha256(Path(__file__)),
            "train_split_sha256": sha256(train_file),
            "valid_split_sha256": sha256(valid_file),
            "test_split_sha256": sha256(test_file),
            "users_sidecar": users_path.name,
            "users_sidecar_sha256": sha256(users_path),
        },
    }
    atomic_json(out_path, artifact)
    print(f"sealed final-evaluation artifact written: {out_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
