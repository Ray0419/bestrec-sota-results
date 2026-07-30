#!/usr/bin/env python3
"""One-shot sealed TEST evaluator for the READY PREREG_EE_V4 family."""

from __future__ import annotations

import argparse
import sys

import torch

import ee_v4_common as common


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=common.ARMS, required=True)
    parser.add_argument("--seed", type=int, choices=common.SEEDS, required=True)
    args = parser.parse_args()
    arm, seed = args.arm, args.seed

    endpoint = common.endpoint_path(arm, seed)
    sidecar = common.endpoint_users_path(arm, seed)
    seal = common.endpoint_seal_path(arm, seed)
    existing = [p.name for p in (endpoint, sidecar, seal) if p.exists()]
    if existing:
        raise RuntimeError(f"sealed TEST attempt already exists; refusing rerun: {existing}")
    if not common.READY.is_file():
        raise RuntimeError("family READY record is missing")

    ready = common.load_json(common.READY)
    expected_ready = common.ready_payload()
    if ready != expected_ready:
        raise RuntimeError("family READY record does not exactly bind all terminal bundles")
    ready_sha = common.sha256(common.READY)
    train = common.validate_training_bundle(
        arm, seed, expected_commit=str(ready["repository_commit"]))
    checkpoint_path = common.best_path(arm, seed)
    common.exclusive_json(seal, {
        "protocol": common.PROTOCOL,
        "state": "sealed_test_attempt_started",
        "arm": arm,
        "seed": seed,
        "repository_commit": ready["repository_commit"],
        "ready_sha256": ready_sha,
        "training_sha256": common.sha256(common.training_path(arm, seed)),
        "checkpoint_sha256": common.sha256(checkpoint_path),
        "started_utc": common.utc_now(),
    })

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        raise RuntimeError("PREREG_EE_V4 sealed evaluation requires CUDA")
    common.verify_upstream()
    common.verify_data(include_test=True)
    common.set_seed(seed)
    model = common.build_model(arm, seed, device)
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    required_checkpoint = {
        "arm", "best_epoch", "best_valid_metrics", "protocol", "repository_commit",
        "seed", "state_dict", "total_params", "trainable_params", "upstream_commit",
    }
    if (set(checkpoint) != required_checkpoint
            or checkpoint["protocol"] != common.PROTOCOL
            or checkpoint["arm"] != arm or checkpoint["seed"] != seed
            or checkpoint["upstream_commit"] != common.UPSTREAM_COMMIT
            or checkpoint["repository_commit"] != ready["repository_commit"]
            or int(checkpoint["best_epoch"]) != int(train["best_epoch"])
            or int(checkpoint["total_params"]) != int(train["total_params"])
            or int(checkpoint["trainable_params"]) != int(train["trainable_params"])):
        raise RuntimeError("selected checkpoint schema/identity drift")
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    metrics, records = common.evaluate_model(
        model, "test", device, keep_records=True, profile=True)
    if records is None or set(records) != {
            "user_index", "target_item_id", "rank0", "ndcg10", "hr10", "rr"}:
        raise RuntimeError("sealed evaluator did not produce exact rank sidecar schema")
    common.atomic_npz(sidecar, records)
    endpoint_value = {
        "protocol": common.PROTOCOL,
        "state": "assessment_complete_sealed",
        "arm": arm,
        "model_type": common.MODEL_TYPES[arm],
        "seed": seed,
        "repository_commit": ready["repository_commit"],
        "upstream_commit": common.UPSTREAM_COMMIT,
        "ready_file": common.READY.name,
        "ready_sha256": ready_sha,
        "seal_file": seal.name,
        "seal_sha256": common.sha256(seal),
        "training_file": common.training_path(arm, seed).name,
        "training_sha256": common.sha256(common.training_path(arm, seed)),
        "checkpoint_file": checkpoint_path.name,
        "checkpoint_sha256": common.sha256(checkpoint_path),
        "selected_epoch": int(checkpoint["best_epoch"]),
        "test_data_sha256": common.DATA_HASHES["test_data.df"],
        "evaluator": {
            "candidate_set": f"all {common.N_ITEMS} items",
            "model_input": "most recent 50 TRAIN+VALID interactions",
            "mask": "complete TRAIN+VALID history; target exception",
            "ties": "strict-greater",
            "rank_definition": "rank0=count(eligible_score > target_score)",
        },
        "metrics": metrics,
        "sidecar_file": sidecar.name,
        "sidecar_sha256": common.sha256(sidecar),
        "environment": common.environment(),
        "completed_utc": common.utc_now(),
    }
    common.exclusive_json(endpoint, endpoint_value)
    print(f"E-E V4 SEALED TEST COMPLETE (metrics withheld): {arm}/{seed}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"E-E V4 SEALED TEST FAILURE: {exc}", file=sys.stderr, flush=True)
        raise
