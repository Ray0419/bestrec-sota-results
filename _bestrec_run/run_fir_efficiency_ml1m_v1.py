# -*- coding: utf-8 -*-
"""Sequestered driver for PREREG_FIR_EFFICIENCY_ML1M_V1.

All training finishes with TEST disabled before any sealed final evaluation.
Record-level data and endpoints remain in the ignored private MovieLens root.
Existing outputs are never overwritten.
"""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time

from acquire_movielens_fir_efficiency_v1 import PRIVATE_ROOT, VIEWS


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PY = Path(sys.executable)
TRAINER = HERE / "run_sasrec_sbert_efficiency_ml1m_v1_frozen.py"
EVALUATOR = HERE / "eval_fir_efficiency_ml1m_v1.py"
STRUCTURAL_TEST = HERE / "test_fir_efficiency_v1.py"
SEQUESTRATION_TEST = HERE / "test_fir_efficiency_sequestration_v1.py"
ADJUDICATOR = HERE / "adjudicate_fir_efficiency_ml1m_v1.py"
PREREGISTRATION = ROOT / "PREREG_FIR_EFFICIENCY_ML1M_V1.md"
PROTOCOL = "PREREG_FIR_EFFICIENCY_ML1M_V1"
CATEGORIES = tuple(VIEWS)
PRIMARY_CATEGORY = "MovieLens1M_R4"
ARMS = ("identity", "shared", "grouped", "lowrank", "learned", "pointwise")
SEEDS = tuple(range(20261101, 20261109))
KERNEL = 16
GROUPS = 8
RANK = 4
SPLIT_DIR = PRIVATE_ROOT / "splits"
RESULT_DIR = PRIVATE_ROOT / "results"
STATUS = PRIVATE_ROOT / "fir_efficiency_ml1m_v1_status.json"


def sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


# Bound once when the long-lived driver starts, before any training or TEST
# endpoint exists.  Subsequent status updates reuse this in-memory value.
ADJUDICATOR_SHA256_LF = sha256_lf(ADJUDICATOR)


def base_args():
    return [
        "--epochs", "20",
        "--batch-size", "256",
        "--max-seq-len", "50",
        "--d-model", "64",
        "--n-layers", "4",
        "--n-heads", "2",
        "--dropout", "0.5",
        "--lr", "0.001",
        "--no-sbert",
        "--eval-every", "1",
        "--eval-subsample", "0",
        "--chunked-full-softmax",
        "--augment-factor", "1",
        "--lr-schedule", "warmup_cosine",
        "--label-smoothing", "0.2",
        "--split-dir", str(SPLIT_DIR.resolve()),
    ]


def path_for(category: str, arm: str, seed: int) -> Path:
    return RESULT_DIR / f"results_{category}_FIREFFML1MV1_{arm}_seed{seed}.json"


def train_cmd(category: str, arm: str, seed: int):
    return [str(PY), str(TRAINER), category, *base_args(),
            "--fir-control", arm,
            "--fir-control-kernel", str(KERNEL),
            "--fir-control-groups", str(GROUPS),
            "--fir-control-rank", str(RANK),
            "--no-test-eval", "--sequester-test-load", "--save-ckpt",
            "--seed", str(seed), "--out", str(path_for(category, arm, seed))]


def artifacts_for(category: str, arm: str, seed: int):
    run = path_for(category, arm, seed)
    stem = run.with_suffix("")
    return {
        "run": run,
        "checkpoint": run.with_suffix(".best.pt"),
        "seal": stem.with_suffix(".finaleval.started.json"),
        "final": stem.with_suffix(".finaleval.json"),
        "users": stem.with_suffix(".finaleval.users.npz"),
    }


def preflight(require_data=False):
    missing_code = [str(path) for path in (
        TRAINER, EVALUATOR, STRUCTURAL_TEST, SEQUESTRATION_TEST,
        ADJUDICATOR, PREREGISTRATION)
                    if not path.exists()]
    if missing_code:
        print("PREFLIGHT FAIL missing code:", missing_code)
        return 1
    test = subprocess.run([str(PY), str(STRUCTURAL_TEST)], cwd=ROOT)
    if test.returncode:
        return test.returncode
    test = subprocess.run([str(PY), str(SEQUESTRATION_TEST)], cwd=ROOT)
    if test.returncode:
        return test.returncode
    test = subprocess.run(
        [str(PY), str(ADJUDICATOR), "--verify-freeze"], cwd=ROOT)
    if test.returncode:
        return test.returncode
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    helptext = subprocess.run(
        [str(PY), str(TRAINER), "--help"], capture_output=True,
        text=True, env=env, encoding="utf-8", cwd=ROOT).stdout or ""
    command = train_cmd(PRIMARY_CATEGORY, ARMS[0], SEEDS[0])
    bad = sorted({flag for flag in command
                  if flag.startswith("--") and flag not in helptext})
    if bad:
        print("PREFLIGHT FAIL unknown trainer flags:", bad)
        return 1
    for arm in ARMS:
        if arm not in helptext:
            print("PREFLIGHT FAIL frozen trainer lacks arm:", arm)
            return 1
    split_files = [SPLIT_DIR / f"{category}.{split}.csv"
                   for category in CATEGORIES
                   for split in ("train", "valid", "test")]
    missing_data = [str(path) for path in split_files if not path.exists()]
    if require_data and missing_data:
        print("PREFLIGHT FAIL: acquisition/splits are absent")
        return 2
    existing = [path for category in CATEGORIES for seed in SEEDS for arm in ARMS
                for path in artifacts_for(category, arm, seed).values()
                if path.exists()]
    print(f"PREFLIGHT OK: {len(CATEGORIES)} views x {len(ARMS)} arms x "
          f"{len(SEEDS)} fresh seeds = {len(CATEGORIES)*len(ARMS)*len(SEEDS)} runs; "
          f"existing protocol artifacts={len(existing)}; "
          f"data={'present' if not missing_data else 'sealed/absent'}")
    print("first command:\n ", " ".join(command))
    return 0


def write_status(state, trained, skipped_train, evaluated, skipped_eval, started):
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATUS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({
        "protocol": PROTOCOL,
        "state": state,
        "trained": trained,
        "skipped_train": skipped_train,
        "evaluated": evaluated,
        "skipped_eval": skipped_eval,
        "total": len(CATEGORIES) * len(ARMS) * len(SEEDS),
        "elapsed_min": round((time.time() - started) / 60.0, 1),
        "adjudicator_sha256_lf": ADJUDICATOR_SHA256_LF,
    }, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, STATUS)


def main():
    if "--preflight" in sys.argv:
        return preflight(require_data=False)
    rc = preflight(require_data=True)
    if rc:
        return rc
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    started = time.time()
    trained = skipped_train = evaluated = skipped_eval = 0
    total = len(CATEGORIES) * len(ARMS) * len(SEEDS)

    # View-major, seed-major ordering completes each matched block together.
    # Exactly one child process/GPU job exists at a time.
    for category in CATEGORIES:
        for seed in SEEDS:
            for arm in ARMS:
                paths = artifacts_for(category, arm, seed)
                if paths["run"].exists():
                    if not paths["checkpoint"].exists():
                        print("INTEGRITY FAIL: run JSON without checkpoint:",
                              paths["run"], flush=True)
                        return 2
                    skipped_train += 1
                    print(f"[train skip {trained+skipped_train}/{total}] "
                          f"{paths['run'].name}", flush=True)
                else:
                    print(f"[train {trained+skipped_train+1}/{total}] "
                          f"{paths['run'].name}", flush=True)
                    child = subprocess.run(train_cmd(category, arm, seed), cwd=ROOT)
                    if child.returncode:
                        write_status("train_failed", trained, skipped_train,
                                     evaluated, skipped_eval, started)
                        return child.returncode
                    trained += 1
                write_status("training", trained, skipped_train,
                             evaluated, skipped_eval, started)

    # TEST remains unopened until every one of the 96 checkpoints exists.
    for category in CATEGORIES:
        for seed in SEEDS:
            for arm in ARMS:
                paths = artifacts_for(category, arm, seed)
                if paths["final"].exists():
                    skipped_eval += 1
                    print(f"[eval skip {evaluated+skipped_eval}/{total}] "
                          f"{paths['final'].name}", flush=True)
                elif paths["seal"].exists():
                    print("INTEGRITY FAIL: incomplete one-shot seal:",
                          paths["seal"], flush=True)
                    write_status("eval_seal_incomplete", trained, skipped_train,
                                 evaluated, skipped_eval, started)
                    return 2
                else:
                    print(f"[eval {evaluated+skipped_eval+1}/{total}] "
                          f"{paths['run'].name}", flush=True)
                    child = subprocess.run(
                        [str(PY), str(EVALUATOR), str(paths["run"])], cwd=ROOT)
                    if child.returncode:
                        write_status("eval_failed", trained, skipped_train,
                                     evaluated, skipped_eval, started)
                        return child.returncode
                    evaluated += 1
                write_status("evaluating", trained, skipped_train,
                             evaluated, skipped_eval, started)

    write_status("complete", trained, skipped_train,
                 evaluated, skipped_eval, started)
    print(f"{PROTOCOL} COMPLETE: trained={trained}, train-skipped={skipped_train}, "
          f"evaluated={evaluated}, eval-skipped={skipped_eval}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
