#!/usr/bin/env python3
"""Train one frozen E-E V4 normal-init SASRec seed without reading TEST."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time

import numpy as np
import torch

import ee_v4_common as common


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def valid_terminal(arm: str, seed: int) -> bool:
    record = common.training_path(arm, seed)
    checkpoint = common.best_path(arm, seed)
    if not record.exists():
        if checkpoint.exists() and not common.latest_path(arm, seed).exists():
            raise RuntimeError("best checkpoint exists without an epoch-boundary resume checkpoint")
        return False
    if not checkpoint.is_file():
        raise RuntimeError("partial terminal E-E V4 training bundle")
    common.validate_training_bundle(arm, seed)
    return True


def rng_state() -> dict[str, object]:
    return {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch_cpu": torch.get_rng_state(),
        "torch_cuda": torch.cuda.get_rng_state_all(),
    }


def restore_rng(value: dict[str, object]) -> None:
    random.setstate(value["python"])
    np.random.set_state(value["numpy"])
    torch.set_rng_state(value["torch_cpu"])
    torch.cuda.set_rng_state_all(value["torch_cuda"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=common.ARMS, required=True)
    parser.add_argument("--seed", type=int, choices=common.SEEDS, required=True)
    args = parser.parse_args()
    arm, seed = args.arm, args.seed
    common.verify_upstream()
    common.verify_data(include_test=False)
    if valid_terminal(arm, seed):
        print(f"E-E V4 terminal bundle already valid: {arm}/{seed}")
        return 0
    if common.latest_path(arm, seed).exists() and not common.best_path(arm, seed).exists():
        raise RuntimeError("resume checkpoint exists without selected-best checkpoint")
    if common.endpoint_path(arm, seed).exists() or common.endpoint_seal_path(arm, seed).exists():
        raise RuntimeError("endpoint exists before terminal training bundle")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        raise RuntimeError("PREREG_EE_V4 requires CUDA")
    config = common.frozen_config(arm, seed)
    started = common.started_path(arm, seed)
    if not started.exists():
        common.exclusive_json(started, {
            "protocol": common.PROTOCOL, "arm": arm, "seed": seed,
            "repository_commit": config["repository_commit"],
            "state": "training_started_test_unread", "test_read_or_scored": False,
        })
    else:
        prior = load_json(started)
        if (prior.get("protocol") != common.PROTOCOL or prior.get("arm") != arm
                or prior.get("seed") != seed or prior.get("test_read_or_scored") is not False
                or prior.get("repository_commit") != config["repository_commit"]):
            raise RuntimeError("E-E V4 STARTED record drift")

    common.set_seed(seed)
    model = common.build_model(arm, seed, device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001, eps=1e-8, weight_decay=1e-6)
    train = common.SeqDataset(common.load_train_frame())
    loader = torch.utils.data.DataLoader(train, batch_size=common.BATCH_SIZE, shuffle=False)
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    start_epoch = 0
    best_epoch = -1
    best_valid = -float("inf")
    best_metrics = None
    counter = 0
    elapsed_prior = 0.0
    latest = common.latest_path(arm, seed)
    if latest.exists():
        state = torch.load(latest, map_location=device, weights_only=False)
        required_resume = {
            "arm", "best_epoch", "best_valid_metrics", "best_valid_ndcg10",
            "completed_epoch", "elapsed_training_seconds", "model_state",
            "optimizer_state", "patience_counter", "protocol", "repository_commit",
            "rng_state", "seed", "upstream_commit",
        }
        if (set(state) != required_resume
                or state.get("protocol") != common.PROTOCOL or state.get("arm") != arm
                or state.get("seed") != seed or state.get("upstream_commit") != common.UPSTREAM_COMMIT
                or state.get("repository_commit") != config["repository_commit"]):
            raise RuntimeError("E-E V4 resume checkpoint drift")
        model.load_state_dict(state["model_state"], strict=True)
        optimizer.load_state_dict(state["optimizer_state"])
        start_epoch = int(state["completed_epoch"]) + 1
        best_epoch = int(state["best_epoch"])
        best_valid = float(state["best_valid_ndcg10"])
        best_metrics = state["best_valid_metrics"]
        counter = int(state["patience_counter"])
        elapsed_prior = float(state["elapsed_training_seconds"])
        restore_rng(state["rng_state"])
        print(f"E-E V4 resume {arm}/{seed} at epoch {start_epoch}", flush=True)

    wall_start = time.perf_counter()
    stopped_epoch = start_epoch - 1
    for epoch in range(start_epoch, common.MAX_EPOCHS):
        model.train()
        loss_sum = 0.0
        n_batches = 0
        for batch in loader:
            seq = batch["seq"].to(device)
            target = batch["next"].to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = model.calculate_infonce_loss(seq, target, 64, 0.07)
            if not torch.isfinite(loss):
                raise RuntimeError(f"non-finite E-E V4 loss at epoch {epoch}")
            loss.backward()
            optimizer.step()
            loss_sum += float(loss.detach())
            n_batches += 1
        valid_metrics, _ = common.evaluate_model(model, "valid", device, keep_records=False)
        valid_ndcg = float(valid_metrics["NDCG@10"])
        if valid_ndcg > best_valid:
            best_valid = valid_ndcg
            best_epoch = epoch
            best_metrics = valid_metrics
            counter = 0
            common.atomic_torch(common.best_path(arm, seed), {
                "protocol": common.PROTOCOL, "arm": arm, "seed": seed,
                "upstream_commit": common.UPSTREAM_COMMIT,
                "repository_commit": config["repository_commit"],
                "best_epoch": best_epoch, "best_valid_metrics": best_metrics,
                "total_params": total_params, "trainable_params": trainable_params,
                "state_dict": model.state_dict(),
            })
        else:
            counter += 1
        elapsed = elapsed_prior + time.perf_counter() - wall_start
        common.atomic_torch(latest, {
            "protocol": common.PROTOCOL, "arm": arm, "seed": seed,
            "upstream_commit": common.UPSTREAM_COMMIT,
            "repository_commit": config["repository_commit"],
            "completed_epoch": epoch, "best_epoch": best_epoch,
            "best_valid_ndcg10": best_valid, "best_valid_metrics": best_metrics,
            "patience_counter": counter, "elapsed_training_seconds": elapsed,
            "model_state": model.state_dict(), "optimizer_state": optimizer.state_dict(),
            "rng_state": rng_state(),
        })
        stopped_epoch = epoch
        print(json.dumps({"arm": arm, "seed": seed, "epoch": epoch,
                          "loss": loss_sum / max(n_batches, 1),
                          "valid_ndcg10": valid_ndcg, "best": best_valid,
                          "counter": counter}), flush=True)
        if counter >= common.PATIENCE:
            break
    if best_epoch < 0 or best_metrics is None or not common.best_path(arm, seed).is_file():
        raise RuntimeError("E-E V4 training produced no valid checkpoint")
    elapsed_total = elapsed_prior + time.perf_counter() - wall_start
    record = {
        "protocol": common.PROTOCOL, "state": "training_complete_test_unread",
        "arm": arm, "model_type": common.MODEL_TYPES[arm], "seed": seed,
        "config": config, "environment": common.environment(),
        "best_epoch": best_epoch, "stopped_epoch": stopped_epoch,
        "best_valid": best_metrics, "checkpoint_file": common.best_path(arm, seed).name,
        "checkpoint_sha256": common.sha256(common.best_path(arm, seed)),
        "total_params": total_params, "trainable_params": trainable_params,
        "training_wall_seconds": float(elapsed_total), "test_read_or_scored": False,
    }
    common.exclusive_json(common.training_path(arm, seed), record)
    print(f"E-E V4 TRAINING COMPLETE TEST UNREAD: {arm}/{seed}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"E-E V4 TRAINING FAILURE: {exc}", file=sys.stderr, flush=True)
        raise
