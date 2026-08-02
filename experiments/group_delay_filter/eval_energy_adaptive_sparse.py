#!/usr/bin/env python3
"""Evaluate original, E90, and E95 late-filter checkpoints."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import torch
from torch.utils.data import DataLoader, SequentialSampler

from eval_sparse_support_transfer import grouped_contrast_stats
from paired_projection_eval import evaluate_masks, model_args, sha256


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--data-name", required=True)
    parser.add_argument("--full", type=Path, required=True)
    parser.add_argument("--e90", type=Path, required=True)
    parser.add_argument("--e95", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=314159)
    parser.add_argument("--device", choices=("cpu", "mps"), default="cpu")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.device == "mps" and not torch.backends.mps.is_available():
        raise SystemExit("MPS was requested but is unavailable")
    device = torch.device(args.device)

    sys.path.insert(0, str(args.source_dir))
    from dataset import RecDataset, generate_rating_matrix_valid, get_user_seqs
    from model.fmlprec import FMLPRecModel

    data_path = args.source_dir / "data" / f"{args.data_name}.txt"
    user_seq, max_item, num_users = get_user_seqs(str(data_path))
    config = model_args(max_item + 1, "full", 16, args.batch_size)
    dataset = RecDataset(config, user_seq, data_type="valid")
    dataloader = DataLoader(
        dataset,
        sampler=SequentialSampler(dataset),
        batch_size=args.batch_size,
        num_workers=0,
    )
    rating_matrix = generate_rating_matrix_valid(
        user_seq, num_users, max_item + 1
    )

    paths = {"F": args.full, "E90": args.e90, "E95": args.e95}
    masks = {"legacy_zero": 0.0, "strict_negative_infinity": -math.inf}
    arm_metrics = {}
    for name, path in paths.items():
        model = FMLPRecModel(config)
        model.load_state_dict(
            torch.load(path, map_location="cpu", weights_only=False)
        )
        model = model.to(device)
        arm_metrics[name] = evaluate_masks(
            model, dataloader, rating_matrix, masks, device
        )
        del model
        if device.type == "mps":
            torch.mps.empty_cache()
        print(f"evaluated {name}: {path.name}")

    contrasts = {
        "E90_minus_F": {"E90": 1.0, "F": -1.0},
        "E95_minus_F": {"E95": 1.0, "F": -1.0},
        "E90_minus_E95": {"E90": 1.0, "E95": -1.0},
    }
    result = {
        "protocol": "ENERGY_ADAPTIVE_SPARSE_FIR_V1",
        "data_name": args.data_name,
        "split": "valid",
        "device": str(device),
        "bootstrap_scope": "strict_negative_infinity/NDCG@10",
        "checkpoints": {
            name: {"path": str(path), "sha256": sha256(path)}
            for name, path in paths.items()
        },
        "masks": {},
    }
    for mask_name in masks:
        metrics = next(iter(arm_metrics.values()))[mask_name]
        mask_result = {"arms": {}, "contrasts": {}}
        for metric_name in metrics:
            by_arm = {
                name: arm_metrics[name][mask_name][metric_name]
                for name in paths
            }
            mask_result["arms"][metric_name] = {
                name: float(values.mean()) for name, values in by_arm.items()
            }
            bootstrap_samples = (
                args.bootstrap_samples
                if mask_name == "strict_negative_infinity"
                and metric_name == "NDCG@10"
                else 0
            )
            mask_result["contrasts"][metric_name] = grouped_contrast_stats(
                by_arm, contrasts, args.seed, bootstrap_samples
            )
        result["masks"][mask_name] = mask_result

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    strict = result["masks"]["strict_negative_infinity"]
    print(json.dumps({
        "NDCG@10_arms": strict["arms"]["NDCG@10"],
        "NDCG@10_contrasts": {
            name: values["delta"]
            for name, values in strict["contrasts"]["NDCG@10"].items()
        },
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

