#!/usr/bin/env python3
"""Custody wrapper around the previously frozen canonical-FIR trainer."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import run_sasrec_sbert_pointwise_v1_frozen as base


PROTOCOL = "PREREG_FIR_PROSPECTIVE_SW_V2"


def sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def take_flag(argv: list[str], flag: str) -> str:
    if flag not in argv:
        raise RuntimeError(f"missing required wrapper flag: {flag}")
    index = argv.index(flag)
    if index + 1 >= len(argv):
        raise RuntimeError(f"missing value for wrapper flag: {flag}")
    value = argv[index + 1]
    del argv[index:index + 2]
    return value


def main() -> int:
    argv = list(sys.argv)
    if "--help" in argv:
        sys.argv = argv
        return int(base.main() or 0)
    execution_head = take_flag(argv, "--execution-git-head")
    protocol = take_flag(argv, "--prospective-protocol")
    if protocol != PROTOCOL:
        raise RuntimeError(f"unexpected protocol: {protocol}")
    if len(execution_head) != 40 or any(c not in "0123456789abcdef" for c in execution_head):
        raise RuntimeError(f"invalid execution Git HEAD: {execution_head}")
    if len(argv) < 2 or argv[1] != "Software":
        raise RuntimeError("wrapper is frozen to Software")
    if "--out" not in argv:
        raise RuntimeError("missing --out")
    out = Path(argv[argv.index("--out") + 1]).resolve()
    if out.exists():
        raise RuntimeError(f"output exists; refusing overwrite: {out}")
    sys.argv = argv
    rc = base.main()
    if rc:
        return int(rc)
    payload = json.loads(out.read_text(encoding="utf-8"))
    if payload.get("best_test") is not None or any(
            "test" in epoch for epoch in payload.get("history", [])):
        raise RuntimeError("base trainer accessed TEST")
    payload["prospective_custody"] = {
        "protocol": PROTOCOL,
        "execution_git_head": execution_head,
        "base_trainer_sha256_lf": sha256_lf(Path(base.__file__)),
        "wrapper_sha256_lf": sha256_lf(Path(__file__)),
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
