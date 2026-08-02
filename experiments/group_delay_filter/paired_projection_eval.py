#!/usr/bin/env python3
"""Paired full-catalog evaluation for an original and projected FMLP checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
from torch.utils.data import DataLoader, SequentialSampler


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def model_args(
    item_size: int,
    filter_mode: str,
    causal_k: int,
    batch_size: int,
) -> SimpleNamespace:
    return SimpleNamespace(
        item_size=item_size,
        batch_size=batch_size,
        max_seq_length=50,
        hidden_size=64,
        num_hidden_layers=2,
        hidden_act="gelu",
        num_attention_heads=2,
        attention_probs_dropout_prob=0.5,
        hidden_dropout_prob=0.5,
        initializer_range=0.02,
        filter_mode=filter_mode,
        causal_k=causal_k,
        model_type="FMLPRec",
    )


def topk_indices(scores: np.ndarray, k: int) -> np.ndarray:
    candidates = np.argpartition(scores, -k, axis=1)[:, -k:]
    candidate_scores = scores[np.arange(len(scores))[:, None], candidates]
    order = np.argsort(candidate_scores, axis=1)[:, ::-1]
    return candidates[np.arange(len(scores))[:, None], order]


@torch.inference_mode()
def evaluate_masks(
    model: torch.nn.Module,
    dataloader: DataLoader,
    rating_matrix,
    mask_values: dict[str, float],
) -> dict[str, dict[str, np.ndarray]]:
    model.eval()
    answers = []
    predictions = {name: [] for name in mask_values}
    for batch in dataloader:
        user_ids, input_ids, batch_answers, _, _ = batch
        sequence = model.predict(input_ids, user_ids)[:, -1, :]
        scores = torch.matmul(sequence, model.item_embeddings.weight.T).numpy()
        seen = rating_matrix[user_ids.numpy()].toarray() > 0
        for name, mask_value in mask_values.items():
            masked_scores = scores.copy()
            masked_scores[seen] = mask_value
            predictions[name].append(topk_indices(masked_scores, 20))
        answers.append(batch_answers.numpy())

    answer = np.concatenate(answers)
    results = {}
    for name, batches in predictions.items():
        predicted = np.concatenate(batches)
        metrics: dict[str, np.ndarray] = {}
        for k in (5, 10, 20):
            matches = predicted[:, :k] == answer[:, None]
            hit = matches.any(axis=1).astype(np.float64)
            ranks = np.argmax(matches, axis=1)
            ndcg = np.where(hit > 0, 1.0 / np.log2(ranks + 2.0), 0.0)
            metrics[f"HR@{k}"] = hit
            metrics[f"NDCG@{k}"] = ndcg
        results[name] = metrics
    return results


def paired_stats(
    baseline: np.ndarray,
    projected: np.ndarray,
    seed: int,
    bootstrap_samples: int,
) -> dict:
    delta = projected - baseline
    generator = np.random.default_rng(seed)
    boot = np.empty(bootstrap_samples, dtype=np.float64)
    for start in range(0, bootstrap_samples, 250):
        size = min(250, bootstrap_samples - start)
        indices = generator.integers(0, len(delta), size=(size, len(delta)))
        boot[start:start + size] = delta[indices].mean(axis=1)
    nonzero = delta[delta != 0]
    return {
        "n_users": int(len(delta)),
        "baseline": float(baseline.mean()),
        "projected": float(projected.mean()),
        "delta": float(delta.mean()),
        "relative_delta": float(delta.mean() / max(baseline.mean(), 1e-15)),
        "bootstrap_95_ci": [
            float(np.quantile(boot, 0.025)),
            float(np.quantile(boot, 0.975)),
        ],
        "users_improved": int((delta > 0).sum()),
        "users_harmed": int((delta < 0).sum()),
        "users_unchanged": int((delta == 0).sum()),
        "nonzero_win_rate": None if len(nonzero) == 0 else float((nonzero > 0).mean()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--data-name", required=True)
    parser.add_argument("--split", choices=("valid", "test"), default="test")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--projected", type=Path, required=True)
    parser.add_argument("--filter-mode", default="full")
    parser.add_argument("--causal-k", type=int, default=16)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=314159)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    sys.path.insert(0, str(args.source_dir))
    from dataset import (
        RecDataset,
        generate_rating_matrix_test,
        generate_rating_matrix_valid,
        get_user_seqs,
    )
    from model.fmlprec import FMLPRecModel

    data_path = args.source_dir / "data" / f"{args.data_name}.txt"
    user_seq, max_item, num_users = get_user_seqs(str(data_path))
    config = model_args(
        max_item + 1, args.filter_mode, args.causal_k, args.batch_size)
    dataset = RecDataset(config, user_seq, data_type=args.split)
    dataloader = DataLoader(
        dataset,
        sampler=SequentialSampler(dataset),
        batch_size=args.batch_size,
        num_workers=0,
    )
    rating_matrix = generate_rating_matrix_test(user_seq, num_users, max_item + 1) \
        if args.split == "test" else \
        generate_rating_matrix_valid(user_seq, num_users, max_item + 1)

    models = []
    for path in (args.baseline, args.projected):
        model = FMLPRecModel(config)
        model.load_state_dict(torch.load(path, map_location="cpu", weights_only=False))
        models.append(model)

    result = {
        "protocol": "PAIRED_PROJECTION_FULL_CATALOG_V1",
        "data_name": args.data_name,
        "split": args.split,
        "filter_mode": args.filter_mode,
        "baseline": {"path": str(args.baseline), "sha256": sha256(args.baseline)},
        "projected": {"path": str(args.projected), "sha256": sha256(args.projected)},
        "masks": {},
    }
    mask_values = {
        "legacy_zero": 0.0,
        "strict_negative_infinity": -math.inf,
    }
    baseline_masks = evaluate_masks(
        models[0], dataloader, rating_matrix, mask_values)
    projected_masks = evaluate_masks(
        models[1], dataloader, rating_matrix, mask_values)
    for mask_name in mask_values:
        baseline = baseline_masks[mask_name]
        projected = projected_masks[mask_name]
        result["masks"][mask_name] = {
            metric: paired_stats(
                baseline[metric], projected[metric], args.seed, args.bootstrap_samples)
            for metric in baseline
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        mask: values["NDCG@10"] for mask, values in result["masks"].items()
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
