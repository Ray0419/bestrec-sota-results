#!/usr/bin/env python3
"""Fail-closed driver for prospective Software FIR V3."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import fir_prospective_sw_v3_common as common


def validate_training_json(path: Path, arm: str, seed: int,
                           head: str, attempt_sha: str) -> dict:
    if not path.is_file() or not path.with_suffix(".best.pt").is_file():
        raise RuntimeError(f"missing training JSON/checkpoint: {path.name}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    cfg = payload.get("config", {})
    custody = payload.get("prospective_custody", {})
    expected_argv = common.expected_trainer_argv(arm, seed, path)
    if (cfg.get("category") != common.CATEGORY
            or cfg.get("seed") != seed
            or cfg.get("epochs") != 20
            or cfg.get("fir_control") != arm
            or cfg.get("fir_control_kernel") != common.KERNEL
            or cfg.get("fir_v3") != "off"
            or cfg.get("causal_filter")
            or not cfg.get("no_test_eval")
            or not cfg.get("save_ckpt")
            or payload.get("best_test") is not None
            or any("test" in epoch for epoch in payload.get("history", []))
            or custody.get("protocol") != common.PROTOCOL
            or custody.get("execution_git_tag") != common.TAG
            or custody.get("execution_git_head") != head
            or custody.get("attempt_sha256") != attempt_sha
            or custody.get("exact_argv") != expected_argv
            or custody.get("exact_argv_sha256") != common.json_sha(expected_argv)
            or custody.get("test_scoring_during_training") is not False):
        raise RuntimeError(f"training artifact violates V3: {path.name}")
    ckpt = path.with_suffix(".best.pt")
    if payload.get("best_ckpt_sha256") != common.sha256(ckpt):
        raise RuntimeError(f"checkpoint digest mismatch: {ckpt.name}")
    if arm == "identity" and payload.get("fir_control_final_l2") != 0.0:
        raise RuntimeError(f"identity taps moved: {path.name}")
    if arm == "learned" and not (payload.get("fir_control_final_l2", 0.0) > 0.0):
        raise RuntimeError(f"learned taps did not move: {path.name}")
    return payload


def all_training_ready() -> bool:
    return all(common.path_for(arm, seed).is_file()
               and common.path_for(arm, seed).with_suffix(".best.pt").is_file()
               for arm, seed in common.ordered_jobs())


def validate_catalog() -> None:
    # Explicitly permitted transductive structural access under V3.
    items: set[str] = set()
    users: set[str] = set()
    counts = {}
    for split in ("train", "valid", "test"):
        path = common.ROOT / "data_5core" / "5core" / "last_out" / f"Software.{split}.csv"
        count = 0
        with path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                items.add(row["parent_asin"])
                users.add(row["user_id"])
                count += 1
        counts[split] = count
    if counts != {"train": 984048, "valid": 146396, "test": 146396}:
        raise RuntimeError(f"split row-count mismatch: {counts}")
    if len(items) != 17591 or len(users) != 146396:
        raise RuntimeError("transductive catalog count mismatch")
    item_map = json.loads((common.ROOT / "cache_5core" /
                           "asin2idx_Software.json").read_text(encoding="utf-8"))
    if item_map != {item: index for index, item in enumerate(sorted(items))}:
        raise RuntimeError("item map is not the sorted all-split union")


def preflight() -> tuple[str, dict]:
    head = common.assert_tagged_tree()
    env = common.assert_environment()
    common.assert_inputs()
    validate_catalog()
    test = subprocess.run([sys.executable, str(common.STRUCTURAL_TEST)],
                          cwd=common.ROOT)
    if test.returncode:
        raise RuntimeError("structural/gradient test failed")
    forbidden = [path.name for arm, seed in common.ordered_jobs()
                 for path in (common.path_for(arm, seed),
                              common.path_for(arm, seed).with_suffix(".best.pt"),
                              common.path_for(arm, seed).with_suffix(".finaleval.json"),
                              common.path_for(arm, seed).with_suffix(".finaleval.users.npz"),
                              common.path_for(arm, seed).with_suffix(".finaleval.started.json"))
                 if path.exists()]
    if forbidden or any(path.exists() for path in
                        (common.ATTEMPT, common.READY, common.ENDPOINTS_COMPLETE,
                         common.ADJUDICATION, common.LOCK)):
        raise RuntimeError(f"V3 attempt/output already exists: {forbidden[:4]}")
    return head, env


def create_attempt(head: str, env: dict) -> str:
    payload = {
        "protocol": common.PROTOCOL,
        "execution_git_tag": common.TAG,
        "execution_git_head": head,
        "created_unix": time.time(),
        "catalog_policy": "explicit transductive all-split reindex; TEST scoring suppressed until READY",
        "jobs": [[arm, seed] for arm, seed in common.ordered_jobs()],
        "exact_argv_sha256": {
            f"{arm}:{seed}": common.json_sha(common.expected_trainer_argv(arm, seed))
            for arm, seed in common.ordered_jobs()
        },
        "runtime": env,
        "input_sha256": common.EXPECTED_INPUT_SHA256,
        "reference_sha256": common.EXPECTED_REFERENCE_SHA256,
        "frozen_file_sha256": {
            rel: common.sha256(common.ROOT / rel) for rel in common.FROZEN_FILES
        },
        "v2_integrity_record_sha256": common.sha256(
            common.ROOT / "FIR_PROSPECTIVE_SW_V2_INTEGRITY.md"),
    }
    common.atomic_json_x(common.ATTEMPT, payload)
    return common.sha256(common.ATTEMPT)


def write_status(state: str, counters: dict, t0: float, head: str,
                 detail: str | None = None) -> None:
    payload = {
        "protocol": common.PROTOCOL,
        "state": state,
        **counters,
        "total_training": 16,
        "total_evaluation": 16,
        "elapsed_min": round((time.time() - t0) / 60, 1),
        "execution_git_head": head,
        "detail": detail,
    }
    tmp = common.STATUS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, common.STATUS)


def create_ready(head: str, attempt_sha: str) -> str:
    artifacts = {}
    backbone = {seed: {} for seed in common.SEEDS}
    for arm, seed in common.ordered_jobs():
        path = common.path_for(arm, seed)
        payload = validate_training_json(path, arm, seed, head, attempt_sha)
        ckpt = path.with_suffix(".best.pt")
        artifacts[f"{arm}:{seed}"] = {
            "run_json": path.name,
            "run_json_sha256": common.sha256(path),
            "checkpoint": ckpt.name,
            "checkpoint_sha256": common.sha256(ckpt),
        }
        backbone[seed][arm] = payload.get("backbone_init_sha256")
    for seed, hashes in backbone.items():
        if None in hashes.values() or len(set(hashes.values())) != 1:
            raise RuntimeError(f"unmatched backbone initialization for seed {seed}")
    common.atomic_json_x(common.READY, {
        "protocol": common.PROTOCOL,
        "execution_git_head": head,
        "created_unix": time.time(),
        "attempt_sha256": attempt_sha,
        "training_artifacts": artifacts,
        "backbone_init_sha256": backbone,
    })
    return common.sha256(common.READY)


def create_endpoints_complete(head: str, attempt_sha: str, ready_sha: str) -> None:
    artifacts = {}
    for arm, seed in common.ordered_jobs():
        run = common.path_for(arm, seed)
        paths = {
            "finaleval": run.with_suffix(".finaleval.json"),
            "users": run.with_suffix(".finaleval.users.npz"),
            "started_seal": run.with_suffix(".finaleval.started.json"),
        }
        if not all(path.is_file() for path in paths.values()):
            raise RuntimeError(f"endpoint set incomplete for {arm}:{seed}")
        artifacts[f"{arm}:{seed}"] = {
            key: {"name": path.name, "sha256": common.sha256(path)}
            for key, path in paths.items()
        }
    common.atomic_json_x(common.ENDPOINTS_COMPLETE, {
        "protocol": common.PROTOCOL,
        "execution_git_head": head,
        "created_unix": time.time(),
        "attempt_sha256": attempt_sha,
        "ready_sha256": ready_sha,
        "artifacts": artifacts,
        "endpoint_semantically_parsed_by_driver": False,
    })


def main() -> int:
    head, env = preflight()
    if "--preflight" in sys.argv:
        print(f"PREFLIGHT OK at immutable tag {common.TAG} -> {head}")
        return 0
    lock_fd = os.open(common.LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    with os.fdopen(lock_fd, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"pid": os.getpid(), "head": head, "started_unix": time.time()}) + "\n")
    t0 = time.time()
    counters = {"trained": 0, "evaluated": 0, "adjudicated": 0}
    attempt_sha = create_attempt(head, env)
    write_status("training", counters, t0, head)
    for index, (arm, seed) in enumerate(common.ordered_jobs(), 1):
        common.assert_tagged_tree()
        print(f"[train {index}/16] {arm} seed {seed}", flush=True)
        child = subprocess.run(common.train_cmd(arm, seed), cwd=common.ROOT)
        if child.returncode:
            write_status("train_failed", counters, t0, head,
                         f"{arm}:{seed} exit {child.returncode}")
            return child.returncode
        validate_training_json(common.path_for(arm, seed), arm, seed,
                               head, attempt_sha)
        counters["trained"] += 1
        write_status("training", counters, t0, head)
    if not all_training_ready():
        raise RuntimeError("all 16 training artifacts are not ready")
    ready_sha = create_ready(head, attempt_sha)
    write_status("ready_for_sealed_evaluation", counters, t0, head)

    for index, (arm, seed) in enumerate(common.ordered_jobs(), 1):
        common.assert_tagged_tree()
        run = common.path_for(arm, seed)
        print(f"[sealed eval {index}/16] {arm} seed {seed}", flush=True)
        child = subprocess.run([sys.executable, str(common.EVALUATOR), str(run)],
                               cwd=common.ROOT)
        if child.returncode:
            write_status("eval_failed", counters, t0, head,
                         f"{arm}:{seed} exit {child.returncode}")
            return child.returncode
        counters["evaluated"] += 1
        write_status("sealed_evaluation", counters, t0, head)
    create_endpoints_complete(head, attempt_sha, ready_sha)
    write_status("adjudicating", counters, t0, head)
    child = subprocess.run([sys.executable, str(common.ADJUDICATOR)],
                           cwd=common.ROOT)
    if child.returncode:
        write_status("adjudication_failed", counters, t0, head,
                     f"exit {child.returncode}")
        return child.returncode
    counters["adjudicated"] = 1
    write_status("complete", counters, t0, head)
    common.LOCK.unlink()
    print(f"{common.PROTOCOL} COMPLETE", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"INTEGRITY FAIL: {exc}", file=sys.stderr)
        raise SystemExit(2)
