# -*- coding: utf-8 -*-
"""Mini k-dial POC driver: MI, {text,id} x {anchor, k4cap, k0cap}, 1 seed.

Rungs share --item-cap-seed 7 => identical capped-item set; contrast is
within-arm (rung vs anchor) on capped-item targets. Sequential on one GPU;
skip-if-exists so a crash/restart resumes where it left off.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN_RUN = r"C:\Users\rayxc\Documents\R\_bestrec_run"
OUT_DIR = os.path.join(HERE, "poc_out")
os.makedirs(OUT_DIR, exist_ok=True)
TRAINER = os.path.join(HERE, "run_sasrec_sbert_kdial.py")
REF = os.path.join(MAIN_RUN, "results_MI_COLDFUSE_base_seed20260736.json")
SEED = 20260736
EXCLUDE = {"seed", "out", "category", "save_ckpt", "eval_every",
           "fir_v3", "fir_v3_kernel", "fir_v3_wd", "zfusion_sweep"}
TEXT_KEYS = {"text_sim_bias", "text_prototypes"}
RUNGS = (("anchor", []),
         ("k4", ["--item-cap-k", "4", "--item-cap-frac", "0.25",
                 "--item-cap-seed", "7"]),
         ("k0", ["--item-cap-k", "0", "--item-cap-frac", "0.25",
                 "--item-cap-seed", "7"]))


def base_argv(cfg, id_arm):
    argv = [cfg["category"]]
    for k in sorted(cfg):
        if k in EXCLUDE or cfg[k] is None or cfg[k] is False:
            continue
        if id_arm and k in TEXT_KEYS:
            continue
        flag = "--" + k.replace("_", "-")
        if cfg[k] is True:
            argv.append(flag)
        else:
            argv += [flag, str(cfg[k])]
    if id_arm:
        argv.append("--no-sbert")
    argv += ["--eval-every", "5"]
    return argv


def main():
    cfg = json.load(open(REF, encoding="utf-8"))["config"]
    py = sys.executable
    # Foreground-safe: detached processes get reaped in this environment, so the
    # driver runs in the foreground and completes at most --max-runs per
    # invocation, exiting cleanly (skip-if-exists resumes the rest).
    max_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    done = 0
    for arm in ("text", "id"):
        for rung, cap_args in RUNGS:
            out = os.path.join(OUT_DIR, f"results_KDIAL_{arm}_{rung}_MI_seed{SEED}.json")
            if os.path.exists(out):
                print(f"SKIP {os.path.basename(out)} (exists)", flush=True)
                continue
            if done >= max_runs:
                print(f"PAUSE: {max_runs} run(s) done this invocation; "
                      f"re-invoke to continue", flush=True)
                return
            cmd = [py, "-u", TRAINER] + base_argv(cfg, arm == "id") + cap_args + [
                "--seed", str(SEED), "--out", out]
            log = out.replace(".json", ".log")
            print(f"LAUNCH {os.path.basename(out)}", flush=True)
            with open(log, "w", encoding="utf-8") as lf:
                rc = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT).returncode
            print(f"DONE   {os.path.basename(out)} rc={rc}", flush=True)
            if rc != 0:
                print(f"ABORT: rc={rc}, see {log}", flush=True)
                sys.exit(rc)
            done += 1
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
