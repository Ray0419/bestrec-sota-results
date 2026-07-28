#!/usr/bin/env python3
"""Train one immutable validation-only official WEARec V1 attempt."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import torch

import wearec_baseline_v1_common as common


def atomic_checkpoint(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, tmp)
    os.replace(tmp, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("tune", "assessment"), required=True)
    parser.add_argument("--preset", choices=common.PRESET_ORDER, required=True)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    if args.phase == "tune" and args.seed != common.TUNE_SEED:
        raise SystemExit("tuning phase requires the frozen tuning seed")
    if args.phase == "assessment" and args.seed not in common.ASSESSMENT_SEEDS:
        raise SystemExit("assessment phase requires a frozen assessment seed")

    out = common.train_output(args.phase, args.preset, args.seed)
    checkpoint = common.checkpoint_path(args.phase, args.preset, args.seed)
    started_seal = out.with_suffix(".started.json")
    if out.exists() or checkpoint.exists() or started_seal.exists():
        raise SystemExit(f"refusing to overwrite/re-enter attempt: {out}")
    common.exclusive_json(
        started_seal,
        {
            "protocol": common.PROTOCOL,
            "phase": args.phase,
            "preset": args.preset,
            "seed": args.seed,
            "state": "started",
        },
    )

    common.verify_upstream()
    _, item_to_id = common.load_catalog()
    bundle = common.load_train_valid(item_to_id)
    if bundle.n_items != common.N_EXPECTED_ITEMS:
        raise RuntimeError("catalog size mismatch")
    common.set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        raise RuntimeError("frozen campaign requires CUDA")
    torch.cuda.reset_peak_memory_stats(device)
    model = common.build_model(args.preset, bundle.n_items).to(device)
    n_params = sum(parameter.numel() for parameter in model.parameters())
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=common.PRESETS[args.preset]["lr"],
        betas=(0.9, 0.999),
        weight_decay=0.0,
    )
    dataset = common.PrefixTrainDataset(bundle.train_sequences)
    generator = torch.Generator()
    generator.manual_seed(args.seed)
    loader = torch.utils.data.DataLoader(
        dataset,
        batch_size=common.BATCH_SIZE,
        shuffle=True,
        generator=generator,
        num_workers=0,
        pin_memory=True,
    )

    best_valid = -1.0
    best_epoch = 0
    stale = 0
    history: list[dict] = []
    train_started = time.perf_counter()
    for epoch in range(1, common.MAX_EPOCHS + 1):
        model.train()
        epoch_started = time.perf_counter()
        total_loss = 0.0
        batches = 0
        for user_ids, input_ids, answers in loader:
            user_ids = user_ids.to(device, non_blocking=True)
            input_ids = input_ids.to(device, non_blocking=True)
            answers = answers.to(device, non_blocking=True)
            unused = torch.zeros_like(answers)
            loss = model.calculate_loss(input_ids, answers, unused, unused, user_ids)
            if not torch.isfinite(loss):
                raise RuntimeError(f"nonfinite training loss at epoch {epoch}")
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            total_loss += float(loss.detach().cpu())
            batches += 1
        valid, _ = common.evaluate(
            model,
            bundle.train_sequences,
            bundle.valid_targets,
            bundle.n_items,
            device,
            keep_records=False,
        )
        value = float(valid["NDCG@10"])
        improved = value > best_valid
        if improved:
            best_valid = value
            best_epoch = epoch
            stale = 0
            atomic_checkpoint(
                checkpoint,
                common.checkpoint_payload(model, args.preset, args.seed, best_epoch, best_valid),
            )
        else:
            stale += 1
        history.append(
            {
                "epoch": epoch,
                "train_loss": total_loss / max(1, batches),
                "epoch_seconds": time.perf_counter() - epoch_started,
                "valid": valid,
                "improved": improved,
                "patience_counter": stale,
            }
        )
        print(
            f"{common.PROTOCOL} {args.phase} {args.preset} seed={args.seed} "
            f"epoch={epoch} loss={history[-1]['train_loss']:.6f} "
            f"valid_ndcg10={value:.8f} best={best_valid:.8f} stale={stale}",
            flush=True,
        )
        if stale >= common.PATIENCE:
            break

    if not checkpoint.is_file() or best_epoch <= 0:
        raise RuntimeError("training completed without a best checkpoint")
    result = {
        "protocol": common.PROTOCOL,
        "state": "training_complete_test_unread",
        "config": common.frozen_config(args.preset, args.seed, args.phase),
        "n_users": len(bundle.user_names),
        "n_items": bundle.n_items,
        "n_train_examples": len(dataset),
        "n_params": n_params,
        "epochs_completed": len(history),
        "best_epoch": best_epoch,
        "best_valid": {
            "NDCG@10": best_valid,
        },
        "history": history,
        "checkpoint": checkpoint.name,
        "checkpoint_sha256": common.sha256(checkpoint),
        "train_seconds": time.perf_counter() - train_started,
        "peak_cuda_memory_bytes": int(torch.cuda.max_memory_allocated(device)),
        "test_read_or_scored": False,
    }
    common.atomic_json(out, result)
    print(f"TRAINING COMPLETE TEST UNREAD: {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
