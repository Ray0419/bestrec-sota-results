#!/usr/bin/env python3
"""Exact-argv custody wrapper for prospective Software FIR V3."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import fir_prospective_sw_v3_common as common
import run_sasrec_sbert_pointwise_v1_frozen as base


def main() -> int:
    argv = list(sys.argv[1:])
    if "--fir-control" not in argv or "--seed" not in argv or "--out" not in argv:
        raise RuntimeError("missing frozen dynamic arguments")
    arm = argv[argv.index("--fir-control") + 1]
    seed = int(argv[argv.index("--seed") + 1])
    out = Path(argv[argv.index("--out") + 1]).resolve()
    expected = common.expected_trainer_argv(arm, seed, out)
    if argv != expected or out != common.path_for(arm, seed).resolve():
        raise RuntimeError("argv differs from the literal frozen V3 command")
    head = common.assert_tagged_tree()
    env = common.assert_environment()
    common.assert_inputs()
    _, attempt_sha = common.load_attempt()
    if out.exists() or out.with_suffix(".best.pt").exists():
        raise RuntimeError("output/checkpoint exists; refusing overwrite")

    # Remove only the two custody-only flags before the frozen base parser.
    base_argv = list(argv)
    for flag in ("--prospective-protocol", "--execution-git-tag"):
        index = base_argv.index(flag)
        del base_argv[index:index + 2]
    sys.argv = [sys.argv[0], *base_argv]
    rc = int(base.main() or 0)
    if rc:
        return rc

    payload = json.loads(out.read_text(encoding="utf-8"))
    cfg = payload.get("config", {})
    if (cfg.get("category") != common.CATEGORY
            or cfg.get("seed") != seed
            or cfg.get("fir_control") != arm
            or cfg.get("fir_control_kernel") != common.KERNEL
            or not cfg.get("no_test_eval")
            or not cfg.get("save_ckpt")
            or payload.get("best_test") is not None
            or any("test" in epoch for epoch in payload.get("history", []))):
        raise RuntimeError("base trainer violated the frozen scoring boundary")
    payload["prospective_custody"] = {
        "protocol": common.PROTOCOL,
        "execution_git_tag": common.TAG,
        "execution_git_head": head,
        "attempt_sha256": attempt_sha,
        "exact_argv": argv,
        "exact_argv_sha256": common.json_sha(argv),
        "runtime": env,
        "frozen_file_sha256": {
            rel: common.sha256(common.ROOT / rel) for rel in common.FROZEN_FILES
        },
        "catalog_policy": "train+validation+TEST rows loaded only for deterministic transductive reindexing; TEST scoring suppressed during training",
        "test_scoring_during_training": False,
    }
    tmp = out.with_suffix(out.suffix + ".custody.tmp")
    with tmp.open("x", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=2, allow_nan=False)
        fh.write("\n")
    os.replace(tmp, out)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"INTEGRITY FAIL: {exc}", file=sys.stderr)
        raise SystemExit(2)
