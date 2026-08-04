#!/usr/bin/env python3
"""One-shot sealed TEST evaluator for a completed WEARec V1 assessment run."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch

import wearec_baseline_v1_common as common


def atomic_npz(path: Path, records: dict[str, np.ndarray]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as handle:
        np.savez_compressed(handle, **records)
    os.replace(tmp, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", choices=common.PRESET_ORDER, required=True)
    parser.add_argument("--seed", type=int, choices=common.ASSESSMENT_SEEDS, required=True)
    args = parser.parse_args()

    train_path = common.train_output("assessment", args.preset, args.seed)
    checkpoint_path = common.checkpoint_path("assessment", args.preset, args.seed)
    endpoint = common.endpoint_path(args.preset, args.seed)
    users_path = common.endpoint_users_path(args.preset, args.seed)
    seal = common.endpoint_seal_path(args.preset, args.seed)
    if endpoint.exists() or users_path.exists() or seal.exists():
        raise SystemExit(f"refusing repeat TEST access: {endpoint}")
    if not train_path.is_file() or not checkpoint_path.is_file():
        raise SystemExit("completed training artifact/checkpoint missing")
    with train_path.open("r", encoding="utf-8") as handle:
        train = json.load(handle)
    if (
        train.get("protocol") != common.PROTOCOL
        or train.get("state") != "training_complete_test_unread"
        or train.get("test_read_or_scored") is not False
        or train.get("config", {}).get("preset") != args.preset
        or train.get("config", {}).get("seed") != args.seed
        or train.get("checkpoint_sha256") != common.sha256(checkpoint_path)
    ):
        raise SystemExit("training artifact provenance mismatch")
    common.exclusive_json(
        seal,
        {
            "protocol": common.PROTOCOL,
            "preset": args.preset,
            "seed": args.seed,
            "state": "final_test_started_no_repeat",
            "checkpoint_sha256": common.sha256(checkpoint_path),
        },
    )

    common.verify_upstream()
    _, item_to_id = common.load_catalog()
    bundle = common.load_train_valid(item_to_id)
    test_targets = common.load_test_targets(bundle, item_to_id)
    histories = [sequence + [bundle.valid_targets[index]] for index, sequence in enumerate(bundle.train_sequences)]
    common.set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        raise RuntimeError("frozen campaign requires CUDA")
    model = common.build_model(args.preset, bundle.n_items).to(device)
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    if (
        checkpoint.get("protocol") != common.PROTOCOL
        or checkpoint.get("preset") != args.preset
        or checkpoint.get("seed") != args.seed
        or checkpoint.get("upstream_commit") != common.UPSTREAM_COMMIT
    ):
        raise RuntimeError("checkpoint metadata mismatch")
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    summary, records = common.evaluate(
        model,
        histories,
        test_targets,
        bundle.n_items,
        device,
        keep_records=True,
    )
    if records is None:
        raise RuntimeError("missing per-user records")
    atomic_npz(users_path, records)
    endpoint_obj = {
        "protocol": common.PROTOCOL,
        "state": "final_test_complete",
        "preset": args.preset,
        "seed": args.seed,
        "upstream_commit": common.UPSTREAM_COMMIT,
        "repository_commit": train["config"]["repository_commit"],
        "checkpoint_sha256": common.sha256(checkpoint_path),
        "train_artifact_sha256": common.sha256(train_path),
        "catalog_sha256": common.CATALOG_SHA256,
        "split_sha256": common.SPLIT_HASHES,
        "candidate_policy": "all 25612 items; padding excluded; complete train+valid history masked -inf",
        "tie_policy": "rank0 = count(candidate_score > target_score)",
        "metrics": summary,
        "perusers_file": users_path.name,
        "perusers_sha256": common.sha256(users_path),
    }
    common.atomic_json(endpoint, endpoint_obj)
    # Never print endpoint values; the committed adjudicator is the first reader.
    print(f"SEALED FINAL TEST COMPLETE: {endpoint.name}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
