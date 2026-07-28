#!/usr/bin/env python3
"""Prepare the TEST-free full-history input used by PREREG_EE_V3 training.

The pre-existing export stores train/valid/test in one JSONL record.  This
one-time prelaunch preparation reads that outcome-known export and emits a
private NPZ containing only user id, complete TRAIN history, and VALID target.
The V3 trainer subsequently has no reason or path to open TEST data.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "ee_baselines" / "export" / "Video_Games" / "Video_Games.sequences.jsonl"
PRIVATE = ROOT / "_bestrec_run" / "ee_v3_private" / "input"
OUT = PRIVATE / "Video_Games.train_valid_full.npz"
MANIFEST = ROOT / "_bestrec_run" / "ee_v3_input_manifest.json"
SOURCE_SHA256 = "402fe06f0aa579f43162fbc15177f9f50a2241277a6b427c1ebf59cde8c72f5b"
N_USERS = 94762
N_ITEMS = 25612


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    os.replace(tmp, path)


def main() -> int:
    if not SOURCE.is_file() or sha256(SOURCE) != SOURCE_SHA256:
        raise SystemExit("E-E V3 source sequence export identity mismatch")
    if OUT.exists():
        raise SystemExit(f"refusing to overwrite private input: {OUT}")
    PRIVATE.mkdir(parents=True, exist_ok=True)
    users: list[int] = []
    offsets = [0]
    flat: list[int] = []
    valid: list[int] = []
    with SOURCE.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            user = int(row["user"])
            train = [int(x) for x in row["train"]]
            target = [int(x) for x in row["valid"]]
            if user != len(users) or not train or len(target) != 1:
                raise SystemExit(f"E-E V3 sequence schema/order failure at user {user}")
            if min(train + target) < 0 or max(train + target) >= N_ITEMS:
                raise SystemExit(f"E-E V3 item range failure at user {user}")
            users.append(user)
            flat.extend(train)
            offsets.append(len(flat))
            valid.append(target[0])
    if len(users) != N_USERS:
        raise SystemExit(f"E-E V3 user count mismatch: {len(users)}")
    tmp = OUT.with_suffix(OUT.suffix + ".tmp")
    with tmp.open("wb") as handle:
        np.savez_compressed(
            handle,
            user_index=np.asarray(users, dtype=np.int64),
            train_offsets=np.asarray(offsets, dtype=np.int64),
            train_items=np.asarray(flat, dtype=np.int64),
            valid_target=np.asarray(valid, dtype=np.int64),
        )
    os.replace(tmp, OUT)
    manifest = {
        "protocol": "PREREG_EE_V3",
        "source": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": SOURCE_SHA256,
        "private_input": str(OUT.relative_to(ROOT)).replace("\\", "/"),
        "private_input_sha256": sha256(OUT),
        "contains_test_fields": False,
        "n_users": len(users),
        "n_items": N_ITEMS,
        "n_train_interactions": len(flat),
        "arrays": {
            "user_index": [len(users)],
            "train_offsets": [len(offsets)],
            "train_items": [len(flat)],
            "valid_target": [len(valid)],
        },
    }
    atomic_json(MANIFEST, manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
