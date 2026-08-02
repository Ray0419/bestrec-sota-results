#!/usr/bin/env python3
"""Fit a 16-parameter shared FIR on a frozen released identity checkpoint."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader


ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = ROOT / "_bestrec_run"
sys.path.insert(0, str(RUN_DIR))

import run_sasrec_sbert as rsp  # noqa: E402
from fuse_ease_eval import build_model_from_config  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260901)
    ap.add_argument("--train-users", type=int, default=5000,
                    help="0 uses every training user")
    ap.add_argument("--train-user-seed", type=int, default=271828)
    ap.add_argument("--eval-users", type=int, default=5000)
    ap.add_argument("--eval-user-seed", type=int, default=314159)
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--lr", type=float, default=0.01)
    ap.add_argument("--weight-decay", type=float, default=0.0)
    ap.add_argument("--sampled-negs", type=int, default=512)
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--threads", type=int,
                    default=max(1, min(8, os.cpu_count() or 1)))
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    device = torch.device("cpu")

    stem = f"results_Musical_Instruments_FIRCTRL_identity_seed{args.seed}"
    run_path = RUN_DIR / f"{stem}.json"
    ckpt_path = RUN_DIR / f"{stem}.best.pt"
    base = json.loads(run_path.read_text(encoding="utf-8"))
    cfg = base["config"]
    category = cfg["category"]

    train_file = rsp.SPLIT_DIR / f"{category}.train.csv"
    valid_file = rsp.SPLIT_DIR / f"{category}.valid.csv"
    test_file = rsp.SPLIT_DIR / f"{category}.test.csv"
    train_rows = rsp.load_split_csv(train_file)
    valid_rows = rsp.load_split_csv(valid_file)
    # Mapping fidelity only; no test target is evaluated.
    test_rows = rsp.load_split_csv(test_file)
    train, valid, _, _, items = rsp.reindex(train_rows, valid_rows, test_rows)
    n_items, pad_id = len(items), len(items)
    all_sequences = rsp.build_user_sequences(train)
    all_times = rsp.build_user_time_sequences(train) if cfg.get("time_bias") else None

    users = np.asarray(sorted(all_sequences))
    if args.train_users and args.train_users < len(users):
        rng = np.random.default_rng(args.train_user_seed)
        users = np.sort(rng.choice(users, args.train_users, replace=False))
    selected = set(int(x) for x in users)
    train_sequences = {u: seq for u, seq in all_sequences.items() if u in selected}
    train_times = None if all_times is None else {
        u: seq for u, seq in all_times.items() if u in selected}

    emb_path = rsp.EMB_CACHE_DIR / f"sbert_titles_{category}.npy"
    sbert = None if cfg.get("no_sbert") else \
        np.load(emb_path).astype(np.float32)[:n_items]
    checkpoint = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    proto = [x.to(device) for x in checkpoint.get("proto_assign", [])] or None
    adapter_cfg = copy.deepcopy(cfg)
    adapter_cfg["fir_control"] = "shared"
    model = build_model_from_config(adapter_cfg, n_items, pad_id, sbert, proto)
    state = {
        k: v for k, v in checkpoint["state_dict"].items()
        if k != "fir_control_module.weight"}
    missing, unexpected = model.load_state_dict(state, strict=False)
    if missing != ["fir_control_module.weight"] or unexpected:
        raise RuntimeError(f"state mismatch: missing={missing}, unexpected={unexpected}")
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    model.fir_control_module.weight.requires_grad_(True)
    model.to(device)

    dataset = rsp.SASRecDataset(
        train_sequences, cfg["max_seq_len"], n_items, pad_id,
        augment_factor=1, user_times=train_times)
    generator = torch.Generator().manual_seed(args.seed)
    loader = DataLoader(
        dataset, batch_size=args.batch_size, shuffle=True,
        collate_fn=rsp.collate_batch, num_workers=0, generator=generator)
    optimizer = torch.optim.AdamW(
        [model.fir_control_module.weight], lr=args.lr,
        weight_decay=args.weight_decay)

    def evaluate() -> dict:
        return rsp.evaluate(
            model, all_sequences, valid, n_items, pad_id,
            cfg["max_seq_len"], device, top_k=10,
            batch_size=args.batch_size, subsample_users=args.eval_users,
            subsample_seed=args.eval_user_seed, user_times=all_times,
            cosine=cfg.get("cosine_scoring", False))

    started = time.time()
    initial = evaluate()
    initial.pop("_user_records")
    history = []
    best = {"epoch": 0, "NDCG@10": initial["NDCG@10"],
            "weight": model.fir_control_module.weight.detach().clone()}
    for epoch in range(1, args.epochs + 1):
        t0 = time.time()
        loss, positions = rsp.train_one_epoch(
            model, loader, optimizer, pad_id, device,
            sampled_negs=args.sampled_negs,
            cosine=cfg.get("cosine_scoring", False),
            temp=cfg.get("score_temp", 1.0))
        metrics = evaluate()
        metrics.pop("_user_records")
        row = {
            "epoch": epoch,
            "train_loss": float(loss),
            "train_positions": int(positions),
            "NDCG@10": float(metrics["NDCG@10"]),
            "HR@10": float(metrics["HR@10"]),
            "kernel": model.fir_control_module.weight.detach().flatten().tolist(),
            "elapsed_seconds": time.time() - t0,
        }
        history.append(row)
        if row["NDCG@10"] > best["NDCG@10"]:
            best = {
                "epoch": epoch, "NDCG@10": row["NDCG@10"],
                "weight": model.fir_control_module.weight.detach().clone()}

    with torch.no_grad():
        model.fir_control_module.weight.copy_(best["weight"])
    final = evaluate()
    final.pop("_user_records")
    artifact = {
        "protocol": "FIR_POSTHOC_ADAPTER_VALIDATION_ONLY_V1",
        "category": category,
        "seed": args.seed,
        "train_users": len(train_sequences),
        "train_user_seed": args.train_user_seed,
        "eval_users": args.eval_users,
        "eval_user_seed": args.eval_user_seed,
        "epochs": args.epochs,
        "lr": args.lr,
        "weight_decay": args.weight_decay,
        "sampled_negs": args.sampled_negs,
        "trainable_parameters": 16,
        "initial": initial,
        "history": history,
        "best_epoch": best["epoch"],
        "best": final,
        "delta_ndcg10": float(final["NDCG@10"] - initial["NDCG@10"]),
        "elapsed_seconds": time.time() - started,
        "provenance": {
            "identity_run": str(run_path.relative_to(ROOT)),
            "identity_run_sha256": sha256(run_path),
            "identity_checkpoint": str(ckpt_path.relative_to(ROOT)),
            "identity_checkpoint_sha256": sha256(ckpt_path),
            "test_usage": "item-ID mapping only; no test target scored",
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "out": str(args.out), "initial_ndcg10": initial["NDCG@10"],
        "best_epoch": best["epoch"], "best_ndcg10": final["NDCG@10"],
        "delta_ndcg10": artifact["delta_ndcg10"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
