# -*- coding: utf-8 -*-
"""Outcome-silent one-shot TEST evaluator for ML1M FIR efficiency V1."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import statistics
import time

import numpy as np
import torch
from torch.utils.flop_counter import FlopCounterMode

import run_sasrec_sbert_efficiency_ml1m_v1_frozen as rsp


PROTOCOL = "PREREG_FIR_EFFICIENCY_ML1M_V1"
ARMS = {"identity", "shared", "grouped", "lowrank", "learned", "pointwise"}
BENCHMARK_BATCH = 256
BENCHMARK_WARMUP = 20
BENCHMARK_REPETITIONS = 50


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def atomic_json(path: Path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2)
    os.replace(tmp, path)


def build_model(cfg, n_items, pad_id):
    return rsp.SASRecSBERT(
        n_items=n_items, pad_id=pad_id,
        max_seq_len=cfg["max_seq_len"], d_model=cfg["d_model"],
        n_layers=cfg["n_layers"], n_heads=cfg["n_heads"],
        dropout=cfg["dropout"], sbert_emb=None,
        fir_control=cfg["fir_control"],
        fir_control_kernel=cfg["fir_control_kernel"],
        fir_control_groups=cfg["fir_control_groups"],
        fir_control_rank=cfg["fir_control_rank"])


def benchmark_inputs(seqs, test, val_extra, max_seq_len, pad_id, device):
    targets = {u: i for u, i, _, _ in test}
    users = sorted(targets)[:BENCHMARK_BATCH]
    rows, last = [], []
    for user in users:
        seq = (seqs.get(user, []) + val_extra.get(user, []))[-max_seq_len:]
        if not seq:
            raise RuntimeError("benchmark user has no history")
        last.append(len(seq) - 1)
        rows.append(seq + [pad_id] * (max_seq_len - len(seq)))
    return (torch.tensor(rows, dtype=torch.long, device=device),
            torch.tensor(last, dtype=torch.long, device=device))


def measure(model, ids, last):
    device = ids.device

    def score_once():
        hidden = model.encode(ids)
        query = hidden[torch.arange(ids.shape[0], device=device), last]
        return query @ model.all_item_features().T

    with torch.inference_mode():
        for _ in range(BENCHMARK_WARMUP):
            score_once()
        if device.type == "cuda":
            torch.cuda.synchronize()
        timings = []
        if device.type == "cuda":
            torch.cuda.reset_peak_memory_stats()
        for _ in range(BENCHMARK_REPETITIONS):
            if device.type == "cuda":
                torch.cuda.synchronize()
            started = time.perf_counter()
            score_once()
            if device.type == "cuda":
                torch.cuda.synchronize()
            timings.append((time.perf_counter() - started) * 1000.0)
        with FlopCounterMode(display=False) as counter:
            score_once()
        flops = int(counter.get_total_flops())
    ordered = sorted(timings)
    p95_index = max(0, int(np.ceil(0.95 * len(ordered))) - 1)
    return {
        "batch_size": int(ids.shape[0]),
        "sequence_length": int(ids.shape[1]),
        "warmup_repetitions": BENCHMARK_WARMUP,
        "timed_repetitions": BENCHMARK_REPETITIONS,
        "latency_ms_median": float(statistics.median(timings)),
        "latency_ms_p95": float(ordered[p95_index]),
        "flops_per_batch": flops,
        "flops_per_user": float(flops / ids.shape[0]),
        "peak_cuda_memory_bytes": (
            int(torch.cuda.max_memory_allocated())
            if device.type == "cuda" else None),
        "device": str(device),
        "cuda_device": (
            torch.cuda.get_device_name(device) if device.type == "cuda" else None),
        "torch": torch.__version__,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_json")
    args = parser.parse_args()
    run_path = Path(args.run_json).resolve()
    ckpt_path = run_path.with_suffix(".best.pt")
    out_path = run_path.with_suffix(".finaleval.json")
    users_path = run_path.with_suffix(".finaleval.users.npz")
    seal_path = run_path.with_suffix(".finaleval.started.json")
    for path in (run_path, ckpt_path):
        if not path.exists():
            raise SystemExit(f"missing required artifact: {path}")
    if out_path.exists() or users_path.exists() or seal_path.exists():
        raise SystemExit("refusing repeat TEST access: final artifact or STARTED seal exists")

    base = json.loads(run_path.read_text(encoding="utf-8"))
    cfg = base["config"]
    arm = cfg.get("fir_control")
    if (arm not in ARMS or cfg.get("fir_control_kernel") != 16
            or cfg.get("fir_control_groups") != 8
            or cfg.get("fir_control_rank") != 4):
        raise SystemExit("run is outside frozen efficiency protocol arms")
    if (not cfg.get("no_test_eval") or not cfg.get("sequester_test_load")
            or not cfg.get("save_ckpt")):
        raise SystemExit("run was not trained with TEST sequestration")
    if base.get("best_test") is not None or any(
            "test" in row for row in base.get("history", [])):
        raise SystemExit("TEST was accessed during training")

    seal = {
        "protocol": PROTOCOL,
        "started_unix": time.time(),
        "run_json": run_path.name,
        "run_json_sha256": sha256(run_path),
        "checkpoint": ckpt_path.name,
        "checkpoint_sha256": sha256(ckpt_path),
    }
    descriptor = os.open(seal_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    with os.fdopen(descriptor, "w", encoding="utf-8") as fh:
        json.dump(seal, fh, indent=2)

    category = cfg["category"]
    split_dir = Path(cfg["split_dir"])
    train_file = split_dir / f"{category}.train.csv"
    valid_file = split_dir / f"{category}.valid.csv"
    test_file = split_dir / f"{category}.test.csv"
    train_rows = rsp.load_split_csv(train_file)
    valid_rows = rsp.load_split_csv(valid_file)
    test_rows = rsp.load_split_csv(test_file)
    train, valid, test, _, items = rsp.reindex(train_rows, valid_rows, test_rows)
    n_items = len(items)
    pad_id = n_items
    seqs = rsp.build_user_sequences(train)
    val_extra = {u: [i] for u, i, _, _ in valid}

    checkpoint = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    model = build_model(cfg, n_items, pad_id)
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    model.to(rsp.DEVICE).eval()
    ids, last = benchmark_inputs(
        seqs, test, val_extra, cfg["max_seq_len"], pad_id,
        torch.device(rsp.DEVICE))
    efficiency = measure(model, ids, last)

    with contextlib.redirect_stdout(io.StringIO()):
        metrics = rsp.evaluate(
            model, seqs, test, n_items, pad_id, cfg["max_seq_len"],
            rsp.DEVICE, top_k=10, batch_size=512,
            extra_history=val_extra,
            cosine=cfg.get("cosine_scoring", False))
    records = metrics.pop("_user_records")
    tmp_users = users_path.with_suffix(users_path.suffix + ".tmp")
    with tmp_users.open("wb") as fh:
        np.savez_compressed(fh, **{
            key: np.asarray(value) for key, value in records.items()})
    os.replace(tmp_users, users_path)

    artifact = {
        "protocol": PROTOCOL,
        "category": category,
        "seed": cfg["seed"],
        "arm": arm,
        "selected_epoch": int(checkpoint["epoch"]),
        "selected_val_NDCG10": float(checkpoint["val_NDCG10"]),
        "test": metrics,
        "efficiency": efficiency,
        "model": {
            "n_params": base["n_params"],
            "n_trainable_params": base["n_trainable_params"],
            "fir_control_trainable_params": base["fir_control_trainable_params"],
            "training_peak_cuda_memory_bytes": base["peak_cuda_memory_bytes"],
            "training_wall_time_s": base["total_wall_time_s"],
        },
        "provenance": {
            **seal,
            "started_seal_sha256": sha256(seal_path),
            "trainer_sha256_lf": sha256_lf(Path(rsp.__file__)),
            "evaluator_sha256_lf": sha256_lf(Path(__file__)),
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
