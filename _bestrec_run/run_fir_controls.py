# -*- coding: utf-8 -*-
"""Sequential Phase-3 active-control campaign (PREREG_FIR_CONTROLS).

Stage 1 trains every arm with validation-only selection and TEST disabled.
Only after all 48 checkpoints exist does Stage 2 invoke the one-shot silent
TEST evaluator. Existing results are never overwritten.
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
TRAINER = os.path.join(HERE, "run_sasrec_sbert.py")
EVALUATOR = os.path.join(HERE, "eval_fir_controls.py")
REF = os.path.join(HERE, "results_MI_V2_ls02_filter16_seed20260608.json")
CATEGORY = "Musical_Instruments"
ARMS = ("identity", "learned", "fixed_ma", "fixed_hp", "shared", "nonlinear")
SEEDS = (20260901, 20260902, 20260903, 20260904,
         20260905, 20260906, 20260907, 20260908)
KERNEL = 16
STATUS = os.path.join(HERE, "fir_controls_status.json")
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
        HERE, f"results_{CATEGORY}_FIRCTRL_{arm}_seed{seed}.json")


def train_cmd(arm, seed):
    out = path_for(arm, seed)
    return [PY, TRAINER, CATEGORY] + base_args() + [
        "--fir-control", arm, "--fir-control-kernel", str(KERNEL),
        "--no-test-eval", "--save-ckpt", "--seed", str(seed),
        "--out", out]


def preflight():
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    helptext = subprocess.run(
        [PY, TRAINER, "--help"], capture_output=True, text=True,
        env=env, encoding="utf-8", cwd=ROOT).stdout or ""
    cmd = train_cmd(ARMS[0], SEEDS[0])
    bad = sorted({x for x in cmd if x.startswith("--") and x not in helptext})
    if bad:
        print("PREFLIGHT FAIL unknown flags:", bad)
        return 1
    if not os.path.exists(EVALUATOR):
        print("PREFLIGHT FAIL missing evaluator")
        return 1
    print(f"PREFLIGHT OK: {len(ARMS)} arms x {len(SEEDS)} seeds; "
          "training precedes all final evaluation")
    print("first command:\n ", " ".join(cmd))
    return 0


def write_status(state, trained, skipped_train, evaluated, skipped_eval, t0):
    tmp = STATUS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({
            "state": state, "trained": trained,
            "skipped_train": skipped_train, "evaluated": evaluated,
            "skipped_eval": skipped_eval, "total": len(ARMS) * len(SEEDS),
            "elapsed_min": round((time.time() - t0) / 60, 1),
        }, f, indent=2)
    os.replace(tmp, STATUS)


def main():
    if "--preflight" in sys.argv:
        return preflight()
    if preflight() != 0:
        return 1
    t0 = time.time()
    trained = skipped_train = evaluated = skipped_eval = 0
    total = len(ARMS) * len(SEEDS)

    # Stage 1: validation-only training. Seed-major ordering completes matched
    # initialization blocks together while retaining one GPU process at a time.
    for seed in SEEDS:
        for arm in ARMS:
            out = path_for(arm, seed)
            ckpt = os.path.splitext(out)[0] + ".best.pt"
            if os.path.exists(out):
                if not os.path.exists(ckpt):
                    print(f"INTEGRITY FAIL: existing {os.path.basename(out)} "
                          "has no best checkpoint", flush=True)
                    return 2
                skipped_train += 1
                print(f"[train skip {trained + skipped_train}/{total}] "
                      f"{os.path.basename(out)}", flush=True)
            else:
                print(f"[train {trained + skipped_train + 1}/{total}] "
                      f"{os.path.basename(out)}", flush=True)
                result = subprocess.run(train_cmd(arm, seed), cwd=ROOT)
                if result.returncode != 0:
                    write_status("train_failed", trained, skipped_train,
                                 evaluated, skipped_eval, t0)
                    return result.returncode
                trained += 1
            write_status("training", trained, skipped_train,
                         evaluated, skipped_eval, t0)

    # Stage 2: exactly one TEST evaluation per best-val checkpoint. The driver
    # tests only existence; it never reads an outcome artifact.
    for seed in SEEDS:
        for arm in ARMS:
            out = path_for(arm, seed)
            final = os.path.splitext(out)[0] + ".finaleval.json"
            started = os.path.splitext(out)[0] + ".finaleval.started.json"
            if os.path.exists(final):
                skipped_eval += 1
                print(f"[eval skip {evaluated + skipped_eval}/{total}] "
                      f"{os.path.basename(final)}", flush=True)
            elif os.path.exists(started):
                print(f"INTEGRITY FAIL: incomplete one-shot evaluation seal: "
                      f"{os.path.basename(started)}", flush=True)
                write_status("eval_seal_incomplete", trained, skipped_train,
                             evaluated, skipped_eval, t0)
                return 2
            else:
                print(f"[eval {evaluated + skipped_eval + 1}/{total}] "
                      f"{os.path.basename(out)}", flush=True)
                result = subprocess.run([PY, EVALUATOR, out], cwd=ROOT)
                if result.returncode != 0:
                    write_status("eval_failed", trained, skipped_train,
                                 evaluated, skipped_eval, t0)
                    return result.returncode
                evaluated += 1
            write_status("evaluating", trained, skipped_train,
                         evaluated, skipped_eval, t0)

    write_status("complete", trained, skipped_train, evaluated, skipped_eval, t0)
    print(f"FIR-CONTROL CAMPAIGN COMPLETE: trained={trained}, "
          f"train-skipped={skipped_train}, evaluated={evaluated}, "
          f"eval-skipped={skipped_eval}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
