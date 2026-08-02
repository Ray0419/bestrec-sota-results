#!/usr/bin/env python3
"""Train a validation-selected FMLP-Rec checkpoint without a test code path."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
from torch.utils.data import DataLoader, RandomSampler, SequentialSampler


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_revision(source_dir: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=source_dir, text=True,
        capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def layer_spectra(state: dict[str, torch.Tensor], threshold: float) -> list[dict]:
    rows = []
    for name, value in state.items():
        if not name.endswith(".complex_weight") or value.shape[-1] != 2:
            continue
        matrix = torch.view_as_complex(value.float().contiguous()).squeeze(0)
        matrix = matrix.clone()
        matrix[0] = matrix[0].real
        matrix[-1] = matrix[-1].real
        singular_values = torch.linalg.svdvals(matrix).double()
        energy = singular_values.square()
        retained = (energy[0] / energy.sum()).item()
        rows.append({
            "parameter": name,
            "shape": list(matrix.shape),
            "canonicalization": "DC and Nyquist responses constrained to real values",
            "rank1_retained_energy": retained,
            "selected": retained >= threshold,
            "singular_values": singular_values.tolist(),
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--data-name", default="ML-100K")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--train-name", required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--expected-data-sha256")
    parser.add_argument("--seed", type=int, default=47)
    parser.add_argument("--device", choices=("cpu", "mps"), default="cpu")
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--threshold", type=float, default=0.905)
    args = parser.parse_args()

    source_dir = args.source_dir.resolve()
    sys.path.insert(0, str(source_dir))
    from dataset import (  # pylint: disable=import-error,import-outside-toplevel
        RecDataset, generate_rating_matrix_valid, get_seq_dic)
    from model import MODEL_DICT  # pylint: disable=import-error,import-outside-toplevel
    from trainers import Trainer  # pylint: disable=import-error,import-outside-toplevel
    from utils import EarlyStopping, set_logger, set_seed  # pylint: disable=import-error,import-outside-toplevel

    args.output_dir.mkdir(parents=True, exist_ok=True)
    data_file = args.data_dir.resolve() / f"{args.data_name}.txt"
    if not data_file.exists():
        raise FileNotFoundError(data_file)
    if not args.preregistration.exists():
        raise FileNotFoundError(args.preregistration)
    data_sha256 = file_hash(data_file)
    if args.expected_data_sha256 and data_sha256 != args.expected_data_sha256:
        raise RuntimeError(
            f"data SHA-256 mismatch: expected {args.expected_data_sha256}, "
            f"found {data_sha256}")

    config = SimpleNamespace(
        data_dir=str(args.data_dir.resolve()) + os.sep,
        output_dir=str(args.output_dir.resolve()),
        data_name=args.data_name,
        train_name=args.train_name,
        model_type="FMLPRec",
        filter_mode="full",
        max_seq_length=50,
        hidden_size=64,
        num_hidden_layers=2,
        hidden_act="gelu",
        num_attention_heads=2,
        attention_probs_dropout_prob=0.5,
        hidden_dropout_prob=0.5,
        initializer_range=0.02,
        batch_size=256,
        lr=0.001,
        weight_decay=0.0,
        adam_beta1=0.9,
        adam_beta2=0.999,
        log_freq=1,
        num_workers=0,
        no_cuda=True,
        device=args.device,
        seed=args.seed,
        fir_arm="off",
        causal_k=16,
    )
    checkpoint = args.output_dir / f"{args.train_name}.pt"
    log_path = args.output_dir / f"{args.train_name}.log"
    artifact_path = args.output_dir / f"{args.train_name}.no_test.json"
    config.checkpoint_path = str(checkpoint)
    config.same_target_path = str(args.data_dir / f"{args.data_name}_same_target.npy")

    set_seed(args.seed)
    logger = set_logger(str(log_path), log_name=f"egsp-{args.train_name}", mode="w")
    sequence, max_item, num_users = get_seq_dic(config)
    config.item_size = max_item + 1
    config.num_users = num_users + 1
    train_data = RecDataset(config, sequence["user_seq"], data_type="train")
    valid_data = RecDataset(config, sequence["user_seq"], data_type="valid")
    train_loader = DataLoader(
        train_data, sampler=RandomSampler(train_data), batch_size=config.batch_size,
        num_workers=0)
    valid_loader = DataLoader(
        valid_data, sampler=SequentialSampler(valid_data), batch_size=config.batch_size,
        num_workers=0)
    config.valid_rating_matrix = generate_rating_matrix_valid(
        sequence["user_seq"], sequence["num_users"], config.item_size)

    logger.info("Protocol TEMPORAL_FILTER_NO_TEST_TRAIN_V2")
    logger.info(str(config))
    model = MODEL_DICT[config.model_type.lower()](args=config)
    trainer = Trainer(model, train_loader, valid_loader, None, config, logger)
    stopper = EarlyStopping(
        str(checkpoint), logger=logger, patience=args.patience, verbose=True)
    best_epoch = None
    last_epoch = None
    for epoch in range(args.epochs):
        trainer.train(epoch)
        scores, _ = trainer.valid(epoch)
        primary = float(scores[-1])
        if stopper.best_score is None or primary > float(stopper.best_score[0]):
            best_epoch = epoch
        stopper(np.array([primary]), trainer.model)
        last_epoch = epoch
        if stopper.early_stop:
            logger.info("Early stopping without test evaluation")
            break

    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    trainer.model.load_state_dict(state)
    validation_scores, validation_info = trainer.valid(best_epoch or 0)
    spectra = layer_spectra(state, args.threshold)
    logger.info(f"Frozen-threshold selected layers: {[r['parameter'] for r in spectra if r['selected']]}")
    logger.info("Training protocol complete; test was not evaluated")
    for handler in logger.handlers:
        handler.flush()

    artifact = {
        "protocol": "TEMPORAL_FILTER_NO_TEST_TRAIN_V2",
        "test_access": "none",
        "completed": True,
        "source_dir": str(source_dir),
        "source_revision": source_revision(source_dir),
        "source_file_sha256": {
            name: file_hash(source_dir / name)
            for name in ("dataset.py", "trainers.py", "model/fmlprec.py")
        },
        "preregistration": str(args.preregistration.resolve()),
        "preregistration_sha256": file_hash(args.preregistration),
        "data_file": str(data_file),
        "data_file_sha256": data_sha256,
        "training_script_sha256": file_hash(Path(__file__)),
        "checkpoint": str(checkpoint.resolve()),
        "checkpoint_sha256": file_hash(checkpoint),
        "log": str(log_path.resolve()),
        "log_sha256": file_hash(log_path),
        "seed": args.seed,
        "device": args.device,
        "last_epoch": last_epoch,
        "best_validation_epoch": best_epoch,
        "checkpoint_selection_metric": "validation NDCG@20",
        "validation_scores": {
            "HR@5": validation_scores[0],
            "NDCG@5": validation_scores[1],
            "HR@10": validation_scores[2],
            "NDCG@10": validation_scores[3],
            "HR@20": validation_scores[4],
            "NDCG@20": validation_scores[5],
            "raw_log_record": validation_info,
        },
        "rank1_energy_threshold": args.threshold,
        "filter_spectra": spectra,
        "selected_layers": [row["parameter"] for row in spectra if row["selected"]],
    }
    artifact_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="ascii")
    print(json.dumps({
        "artifact": str(artifact_path),
        "best_validation_epoch": best_epoch,
        "selected_layers": artifact["selected_layers"],
        "rank1_energies": [row["rank1_retained_energy"] for row in spectra],
        "test_access": "none",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
