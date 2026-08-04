#!/usr/bin/env python3
"""Outcome-silent one-shot TEST evaluator for prospective Software FIR V3."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import time
from pathlib import Path

import numpy as np
import torch

import fir_prospective_sw_v3_common as common
import fuse_ease_eval as model_builder
import run_fir_prospective_sw_v3 as campaign
import run_sasrec_sbert_pointwise_v1_frozen as rsp


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_json")
    args = parser.parse_args()
    head = common.assert_tagged_tree()
    common.assert_environment()
    common.assert_inputs()
    _, attempt_sha = common.load_attempt()
    ready, ready_sha = common.load_ready()

    run_path = Path(args.run_json).resolve()
    allowed = {common.path_for(arm, seed).resolve(): (arm, seed)
               for arm, seed in common.ordered_jobs()}
    if run_path not in allowed:
        raise RuntimeError("run path is outside the frozen V3 campaign")
    arm, seed = allowed[run_path]
    ckpt_path = run_path.with_suffix(".best.pt")
    out_path = run_path.with_suffix(".finaleval.json")
    users_path = run_path.with_suffix(".finaleval.users.npz")
    seal_path = run_path.with_suffix(".finaleval.started.json")
    if out_path.exists() or users_path.exists() or seal_path.exists():
        raise RuntimeError("refusing repeated TEST scoring")

    # Validate every training pair and its READY digest before first scoring.
    for candidate_arm, candidate_seed in common.ordered_jobs():
        candidate = common.path_for(candidate_arm, candidate_seed)
        campaign.validate_training_json(candidate, candidate_arm, candidate_seed,
                                        head, attempt_sha)
        record = ready["training_artifacts"][f"{candidate_arm}:{candidate_seed}"]
        if (record["run_json_sha256"] != common.sha256(candidate)
                or record["checkpoint_sha256"] != common.sha256(
                    candidate.with_suffix(".best.pt"))):
            raise RuntimeError("READY training digest mismatch")

    base = json.loads(run_path.read_text(encoding="utf-8"))
    cfg = base["config"]
    custody = base["prospective_custody"]
    seal = {
        "protocol": common.PROTOCOL,
        "started_unix": time.time(),
        "execution_git_tag": common.TAG,
        "execution_git_head": head,
        "attempt_sha256": attempt_sha,
        "ready_sha256": ready_sha,
        "run_json": run_path.name,
        "run_json_sha256": common.sha256(run_path),
        "checkpoint": ckpt_path.name,
        "checkpoint_sha256": common.sha256(ckpt_path),
        "exact_argv_sha256": custody["exact_argv_sha256"],
    }
    fd = os.open(seal_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(seal, fh, indent=2, allow_nan=False)
        fh.write("\n")

    train_file = rsp.SPLIT_DIR / "Software.train.csv"
    valid_file = rsp.SPLIT_DIR / "Software.valid.csv"
    test_file = rsp.SPLIT_DIR / "Software.test.csv"
    train_rows = rsp.load_split_csv(train_file)
    valid_rows = rsp.load_split_csv(valid_file)
    test_rows = rsp.load_split_csv(test_file)
    train, valid, test, _, items = rsp.reindex(train_rows, valid_rows, test_rows)
    n_items = len(items)
    pad_id = n_items
    seqs = rsp.build_user_sequences(train)
    times = (rsp.build_user_time_sequences(train)
             if cfg.get("time_bias") or cfg.get("time_decay_kernel") else None)
    val_extra: dict[int, list[int]] = {}
    val_times: dict[int, list[int]] = {}
    for user, item, _, timestamp in valid:
        val_extra.setdefault(user, []).append(item)
        val_times.setdefault(user, []).append(timestamp // 1000)
    emb_path = common.ROOT / "cache_5core" / "sbert_titles_Software.npy"
    sbert = np.load(emb_path).astype(np.float32)
    if sbert.shape != (n_items, 384):
        raise RuntimeError(f"title-cache shape mismatch: {sbert.shape}")

    checkpoint = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    proto = [value.to(rsp.DEVICE)
             for value in checkpoint.get("proto_assign", [])] or None
    model_builder.rsp = rsp
    model = model_builder.build_model_from_config(
        cfg, n_items, pad_id, sbert, proto)
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    model.to(rsp.DEVICE).eval()
    with contextlib.redirect_stdout(io.StringIO()):
        metrics = rsp.evaluate(
            model, seqs, test, n_items, pad_id, cfg["max_seq_len"],
            rsp.DEVICE, top_k=10, batch_size=512,
            extra_history=val_extra, user_times=times, extra_times=val_times,
            cosine=cfg.get("cosine_scoring", False))
    records = metrics.pop("_user_records")
    tmp_users = users_path.with_suffix(users_path.suffix + ".tmp")
    with tmp_users.open("xb") as fh:
        np.savez_compressed(
            fh, **{key: np.asarray(value) for key, value in records.items()})
    os.replace(tmp_users, users_path)

    artifact = {
        "protocol": common.PROTOCOL,
        "category": common.CATEGORY,
        "seed": seed,
        "arm": arm,
        "selected_epoch": int(checkpoint["epoch"]),
        "selected_val_NDCG10": float(checkpoint["val_NDCG10"]),
        "test": metrics,
        "provenance": {
            **seal,
            "started_seal_sha256": common.sha256(seal_path),
            "evaluator_self_sha256": common.sha256(Path(__file__)),
            "base_trainer_sha256": common.sha256(common.BASE_TRAINER),
            "model_builder_sha256": common.sha256(common.MODEL_BUILDER),
            "train_split_sha256": common.sha256(train_file),
            "valid_split_sha256": common.sha256(valid_file),
            "test_split_sha256": common.sha256(test_file),
            "title_cache_sha256": common.sha256(emb_path),
            "users_sidecar": users_path.name,
            "users_sidecar_sha256": common.sha256(users_path),
            "catalog_policy": custody["catalog_policy"],
        },
    }
    common.atomic_json_x(out_path, artifact)
    print(f"sealed endpoint written without metric output: {out_path.name}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"INTEGRITY FAIL: {exc}")
        raise SystemExit(2)
