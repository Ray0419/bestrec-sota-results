# -*- coding: utf-8 -*-
"""Sequestered driver for PREREG_FIR_POINTWISE_V1.

Stage 1 trains all arms with TEST disabled. Stage 2 begins only when every
best-validation checkpoint exists, and invokes the silent one-shot evaluator.
Existing outputs are never overwritten.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable
TRAINER = os.path.join(HERE, "run_sasrec_sbert_pointwise_v1_frozen.py")
EVALUATOR = os.path.join(HERE, "eval_fir_pointwise_v1.py")
STRUCTURAL_TEST = os.path.join(HERE, "test_fir_pointwise_v1.py")
REF = os.path.join(HERE, "results_MI_V2_ls02_filter16_seed20260608.json")
CATEGORY = "Musical_Instruments"
PROTOCOL = "PREREG_FIR_POINTWISE_V1"
ARMS = ("identity", "learned", "pointwise")
SEEDS = tuple(range(20261001, 20261009))
KERNEL = 16
STATUS = os.path.join(HERE, "fir_pointwise_v1_status.json")
EXCLUDE = {
    "category", "seed", "out", "causal_filter", "filter_kernel",
    "filter_fixed_avg", "filter_no_gate", "fir_v3", "fir_v3_kernel",
    "fir_v3_wd", "fir_control", "fir_control_kernel", "no_test_eval",
    "save_ckpt",
}


def base_args():
    cfg = json.load(open(REF, encoding="utf-8"))["config"]
    argv = []
    for key in sorted(cfg):
        if key in EXCLUDE:
            continue
        value = cfg[key]
        if value is None or value is False:
            continue
        flag = "--" + key.replace("_", "-")
        argv += [flag] if value is True else [flag, str(value)]
    return argv


def path_for(arm, seed):
    return os.path.join(
        HERE, f"results_{CATEGORY}_FIRPOINTV1_{arm}_seed{seed}.json")


def train_cmd(arm, seed):
    return [PY, TRAINER, CATEGORY] + base_args() + [
        "--fir-control", arm,
        "--fir-control-kernel", str(KERNEL),
        "--no-test-eval", "--save-ckpt",
        "--seed", str(seed), "--out", path_for(arm, seed)]


def preflight():
    for path in (TRAINER, EVALUATOR, STRUCTURAL_TEST, REF):
        if not os.path.exists(path):
            print("PREFLIGHT FAIL missing:", path)
            return 1
    test = subprocess.run([PY, STRUCTURAL_TEST], cwd=ROOT)
    if test.returncode != 0:
        return test.returncode
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    helptext = subprocess.run(
        [PY, TRAINER, "--help"], capture_output=True, text=True,
        env=env, encoding="utf-8", cwd=ROOT).stdout or ""
    cmd = train_cmd(ARMS[0], SEEDS[0])
    bad = sorted({x for x in cmd if x.startswith("--") and x not in helptext})
    if bad:
        print("PREFLIGHT FAIL unknown flags:", bad)
        return 1
    if "pointwise" not in helptext:
        print("PREFLIGHT FAIL frozen trainer lacks pointwise arm")
        return 1
    existing = []
    for seed in SEEDS:
        for arm in ARMS:
            p = path_for(arm, seed)
            for suffix in ("", ".best.pt", ".finaleval.started.json",
                           ".finaleval.json", ".finaleval.users.npz"):
                q = os.path.splitext(p)[0] + suffix if suffix else p
                if os.path.exists(q):
                    existing.append(os.path.basename(q))
    print(f"PREFLIGHT OK: {len(ARMS)} arms x {len(SEEDS)} fresh seeds; "
          f"existing protocol artifacts={len(existing)}")
    print("first command:\n ", " ".join(cmd))
    return 0


def write_status(state, trained, skipped_train, evaluated, skipped_eval, t0):
    tmp = STATUS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({
            "protocol": PROTOCOL,
            "state": state,
            "trained": trained,
            "skipped_train": skipped_train,
            "evaluated": evaluated,
            "skipped_eval": skipped_eval,
            "total": len(ARMS) * len(SEEDS),
            "elapsed_min": round((time.time() - t0) / 60, 1),
        }, f, indent=2)
    os.replace(tmp, STATUS)


def main():
    if "--preflight" in sys.argv:
        return preflight()
    rc = preflight()
    if rc:
        return rc
    t0 = time.time()
    trained = skipped_train = evaluated = skipped_eval = 0
    total = len(ARMS) * len(SEEDS)

    # Seed-major ordering completes matched initialization blocks together.
    # Only one child process (and therefore one GPU job) exists at a time.
    for seed in SEEDS:
        for arm in ARMS:
            out = path_for(arm, seed)
            ckpt = os.path.splitext(out)[0] + ".best.pt"
            if os.path.exists(out):
                if not os.path.exists(ckpt):
                    print("INTEGRITY FAIL: run JSON without checkpoint:", out,
                          flush=True)
                    return 2
                skipped_train += 1
                print(f"[train skip {trained + skipped_train}/{total}] "
                      f"{os.path.basename(out)}", flush=True)
            else:
                print(f"[train {trained + skipped_train + 1}/{total}] "
                      f"{os.path.basename(out)}", flush=True)
                child = subprocess.run(train_cmd(arm, seed), cwd=ROOT)
                if child.returncode:
                    write_status("train_failed", trained, skipped_train,
                                 evaluated, skipped_eval, t0)
                    return child.returncode
                trained += 1
            write_status("training", trained, skipped_train,
                         evaluated, skipped_eval, t0)

    for seed in SEEDS:
        for arm in ARMS:
            out = path_for(arm, seed)
            stem = os.path.splitext(out)[0]
            final = stem + ".finaleval.json"
            seal = stem + ".finaleval.started.json"
            if os.path.exists(final):
                skipped_eval += 1
                print(f"[eval skip {evaluated + skipped_eval}/{total}] "
                      f"{os.path.basename(final)}", flush=True)
            elif os.path.exists(seal):
                print("INTEGRITY FAIL: incomplete one-shot seal:", seal,
                      flush=True)
                write_status("eval_seal_incomplete", trained, skipped_train,
                             evaluated, skipped_eval, t0)
                return 2
            else:
                print(f"[eval {evaluated + skipped_eval + 1}/{total}] "
                      f"{os.path.basename(out)}", flush=True)
                child = subprocess.run([PY, EVALUATOR, out], cwd=ROOT)
                if child.returncode:
                    write_status("eval_failed", trained, skipped_train,
                                 evaluated, skipped_eval, t0)
                    return child.returncode
                evaluated += 1
            write_status("evaluating", trained, skipped_train,
                         evaluated, skipped_eval, t0)

    write_status("complete", trained, skipped_train,
                 evaluated, skipped_eval, t0)
    print(f"{PROTOCOL} COMPLETE: trained={trained}, "
          f"train-skipped={skipped_train}, evaluated={evaluated}, "
          f"eval-skipped={skipped_eval}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
