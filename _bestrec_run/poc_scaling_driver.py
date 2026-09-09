# -*- coding: utf-8 -*-
"""PREREG_SCALING_V1 driver: 4 cold-pool sizes x 3 seeds = 12 MI runs, text arm.

Only --item-cap-frac varies; eligibility (min-deg 20), cap seed, dose (k=0) and
everything else are held fixed, so smaller pools are nested subsets of larger
ones and the exponent is not confounded by item population (which the earlier
3-point estimate was).
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN_RUN = r"C:\Users\rayxc\Documents\R\_bestrec_run"
OUT = os.path.join(HERE, "poc_out")
TRAINER = os.path.join(HERE, "run_sasrec_sbert_kdial.py")
REF = os.path.join(MAIN_RUN, "results_MI_COLDFUSE_base_seed20260736.json")
SEEDS = (20260736, 20260737, 20260738)
FRACS = (0.05, 0.10, 0.25, 0.50)
EXCLUDE = {"seed", "out", "category", "save_ckpt", "eval_every",
           "fir_v3", "fir_v3_kernel", "fir_v3_wd", "zfusion_sweep"}
GPU_BUSY_MIB = 6000


def gpu_busy():
    try:
        o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                            "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=30)
        return int(o.stdout.strip().splitlines()[0]) >= GPU_BUSY_MIB
    except Exception:
        return False


def main():
    max_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    cfg = json.load(open(REF, encoding="utf-8"))["config"]
    base = [cfg["category"]]
    for k in sorted(cfg):
        if k in EXCLUDE or cfg[k] is None or cfg[k] is False:
            continue
        f = "--" + k.replace("_", "-")
        base.append(f) if cfg[k] is True else base.extend([f, str(cfg[k])])
    base += ["--eval-every", "5"]

    done = todo = 0
    for seed in SEEDS:
        for frac in FRACS:
            tag = f"f{frac:g}".replace(".", "")
            out = os.path.join(OUT, f"results_SCAL_{tag}_MI_seed{seed}.json")
            if os.path.exists(out):
                continue
            todo += 1
            if done >= max_runs:
                continue
            if gpu_busy():
                print("GPU BUSY — stopping without launching.", flush=True)
                return
            cmd = ([sys.executable, "-u", TRAINER] + base
                   + ["--item-cap-k", "0", "--item-cap-frac", str(frac),
                      "--item-cap-min-deg", "20", "--item-cap-seed", "7",
                      "--save-ckpt", "--seed", str(seed), "--out", out])
            print(f"LAUNCH {os.path.basename(out)}", flush=True)
            with open(out.replace(".json", ".log"), "w", encoding="utf-8") as lf:
                rc = subprocess.run(cmd, stdout=lf,
                                    stderr=subprocess.STDOUT).returncode
            print(f"DONE   {os.path.basename(out)} rc={rc}", flush=True)
            if rc != 0:
                sys.exit(rc)
            done += 1
    print(f"[{done} run(s) this invocation; {todo-done} remaining]", flush=True)
    if todo - done == 0:
        print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
