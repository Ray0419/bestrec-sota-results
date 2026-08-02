#!/usr/bin/env python3
"""Validation-only paired evaluation of post-hoc causal-FIR projections."""

from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

import numpy as np
import torch


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def without_records(metrics: dict) -> dict:
    return {key: value for key, value in metrics.items() if key != "_user_records"}


def bootstrap_mean_interval(
    values: np.ndarray, seed: int = 271828, draws: int = 5000
) -> list[float]:
    rng = np.random.RandomState(seed)
    means = np.empty(draws, dtype=np.float64)
    batch = 100
    for start in range(0, draws, batch):
        stop = min(start + batch, draws)
        indices = rng.randint(0, len(values), size=(stop - start, len(values)))
        means[start:stop] = values[indices].mean(axis=1)
    return [float(x) for x in np.quantile(means, [0.025, 0.975])]


def paired_summary(base: dict, projected: dict) -> dict:
    base_users = np.asarray(base["user_id"])
    projected_users = np.asarray(projected["user_id"])
    if not np.array_equal(base_users, projected_users):
        raise RuntimeError("paired evaluations contain different users")
    base_ndcg = np.asarray(base["ndcg10"], dtype=np.float64)
    projected_ndcg = np.asarray(projected["ndcg10"], dtype=np.float64)
    delta = projected_ndcg - base_ndcg
    base_rank = np.asarray(base["rank0"], dtype=np.int64)
    projected_rank = np.asarray(projected["rank0"], dtype=np.int64)
    return {
        "n_users": int(len(delta)),
        "ndcg10_delta": float(delta.mean()),
        "ndcg10_delta_bootstrap_95": bootstrap_mean_interval(delta),
        "users_improved": int((delta > 0).sum()),
        "users_harmed": int((delta < 0).sum()),
        "users_unchanged": int((delta == 0).sum()),
        "rank_improved": int((projected_rank < base_rank).sum()),
        "rank_harmed": int((projected_rank > base_rank).sum()),
        "rank_unchanged": int((projected_rank == base_rank).sum()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--subsample-users", type=int, default=10000)
    parser.add_argument("--subsample-seed", type=int, default=314159)
    parser.add_argument(
        "--projections", nargs="+", choices=("rank1", "shared"),
        default=("rank1", "shared"),
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    source_dir = root / "_bestrec_run"
    sys.path.insert(0, str(source_dir))
    import run_sasrec_sbert as rsp  # pylint: disable=import-error,import-outside-toplevel
    from fuse_ease_eval import (  # pylint: disable=import-error,import-outside-toplevel
        build_model_from_config,
    )

    run_path = args.run_json.resolve()
    checkpoint_path = run_path.with_suffix(".best.pt")
    for path in (run_path, checkpoint_path):
        if not path.exists():
            raise FileNotFoundError(path)
    run = json.loads(run_path.read_text(encoding="utf-8"))
    config = run["config"]
    if config.get("fir_control") != "learned":
        raise RuntimeError("source run must use fir_control=learned")
    if not config.get("no_test_eval"):
        raise RuntimeError("source run did not sequester test during training")

    category = config["category"]
    train_path = rsp.SPLIT_DIR / f"{category}.train.csv"
    valid_path = rsp.SPLIT_DIR / f"{category}.valid.csv"
    test_catalog_path = rsp.SPLIT_DIR / f"{category}.test.csv"
    train_rows = rsp.load_split_csv(train_path)
    valid_rows = rsp.load_split_csv(valid_path)
    with test_catalog_path.open("r", encoding="utf-8") as handle:
        test_catalog_items = {
            row["parent_asin"] for row in csv.DictReader(handle)
        }
    users = sorted({row[0] for row in train_rows + valid_rows})
    items = sorted(
        {row[1] for row in train_rows + valid_rows} | test_catalog_items
    )
    user_index = {value: index for index, value in enumerate(users)}
    item_index = {value: index for index, value in enumerate(items)}

    def reindex_rows(rows):
        return [
            (user_index[user], item_index[item], rating, timestamp)
            for user, item, rating, timestamp in rows
        ]

    train = reindex_rows(train_rows)
    valid = reindex_rows(valid_rows)
    n_items = len(items)
    pad_id = n_items
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    expected_items = checkpoint["state_dict"]["item_emb.weight"].shape[0] - 1
    if n_items != expected_items:
        raise RuntimeError(
            f"train+validation catalog has {n_items} items; checkpoint expects "
            f"{expected_items}; refusing to inspect test to reconstruct it"
        )

    sequences = rsp.build_user_sequences(train)
    user_times = (
        rsp.build_user_time_sequences(train)
        if config.get("time_bias") or config.get("time_decay_kernel")
        else None
    )
    cache = config.get("encoder_cache")
    embedding_path = (
        Path(cache) if cache else rsp.EMB_CACHE_DIR / f"sbert_titles_{category}.npy"
    )
    sbert = None
    if not config.get("no_sbert"):
        sbert = np.load(embedding_path).astype(np.float32)[:n_items]
    proto = [value.to("cpu") for value in checkpoint.get("proto_assign", [])] or None
    model = build_model_from_config(config, n_items, pad_id, sbert, proto)
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    model.to("cpu").eval()

    evaluate_args = dict(
        user_seqs=sequences,
        test_inters=valid,
        n_items=n_items,
        pad_id=pad_id,
        max_seq_len=config["max_seq_len"],
        device="cpu",
        top_k=10,
        batch_size=512,
        subsample_users=args.subsample_users,
        subsample_seed=args.subsample_seed,
        user_times=user_times,
        cosine=config.get("cosine_scoring", False),
    )
    with contextlib.redirect_stdout(io.StringIO()):
        baseline = rsp.evaluate(model, **evaluate_args)

    parameter = "fir_control_module.weight"
    original = checkpoint["state_dict"][parameter].detach().clone()
    matrix = original[:, 0, :].float()
    singular_values = torch.linalg.svdvals(matrix).double()
    retained = float(singular_values[0].square() / singular_values.square().sum())
    output = {
        "protocol": "CAUSAL_FIR_POSTHOC_PROJECTION_VALIDATION_V1",
        "test_access": (
            "candidate metadata only: parent_asin column used to reconstruct "
            "the trained catalog; no test user-target associations scored"
        ),
        "test_catalog_file_sha256": file_hash(test_catalog_path),
        "source_run": str(run_path),
        "source_run_sha256": file_hash(run_path),
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": file_hash(checkpoint_path),
        "seed": config["seed"],
        "category": category,
        "subsample_users": args.subsample_users,
        "subsample_seed": args.subsample_seed,
        "delta_kernel_shape": list(matrix.shape),
        "delta_kernel_rank1_retained_energy": retained,
        "baseline": without_records(baseline),
        "projections": {},
    }
    baseline_records = baseline["_user_records"]
    for name in args.projections:
        if name == "rank1":
            left, values, right = torch.linalg.svd(matrix, full_matrices=False)
            projected_matrix = values[0] * torch.outer(left[:, 0], right[0])
            compact_parameters = matrix.shape[0] + matrix.shape[1]
        else:
            projected_matrix = matrix.mean(dim=0, keepdim=True).expand_as(matrix)
            compact_parameters = matrix.shape[1]
        with torch.no_grad():
            model.fir_control_module.weight.copy_(
                projected_matrix[:, None, :].to(original.dtype)
            )
        with contextlib.redirect_stdout(io.StringIO()):
            metrics = rsp.evaluate(model, **evaluate_args)
        output["projections"][name] = {
            "metrics": without_records(metrics),
            "paired": paired_summary(baseline_records, metrics["_user_records"]),
            "compact_parameters": int(compact_parameters),
            "original_parameters": int(matrix.numel()),
            "filter_parameter_reduction_fraction": float(
                1.0 - compact_parameters / matrix.numel()
            ),
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="ascii")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
