# -*- coding: utf-8 -*-
"""PREREG_TRAINED_V1: T1 / T2a / T2b on MI, 3 seeds, temporal protocol."""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN_RUN = r"C:\Users\rayxc\Documents\R\_bestrec_run"
OUT = os.path.join(HERE, "poc_out")
TRAINER = os.path.join(HERE, "run_sasrec_sbert_temporal.py")
REF = os.path.join(MAIN_RUN, "results_MI_COLDFUSE_base_seed20260736.json")
SEEDS = (20260736, 20260737, 20260738)
EXCLUDE = {"seed", "out", "category", "save_ckpt", "eval_every",
           "fir_v3", "fir_v3_kernel", "fir_v3_wd", "zfusion_sweep"}
ARMS = {
    "T1":  ["--content-anchor", "--delta-max", "0.1"],
    "T2a": ["--pseudo-cold-frac", "0.15"],
    "T2b": ["--pseudo-cold-frac", "0.15", "--pool-ce-weight", "0.5"],
}
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
    base += ["--eval-every", "20", "--temporal-split",
             "--temporal-inner-q", "0.60", "--temporal-outer-q", "0.75"]
    done = todo = 0
    for arm, extra in ARMS.items():
        for seed in SEEDS:
            out = os.path.join(OUT, f"results_TRN_{arm}_MI_seed{seed}.json")
            if os.path.exists(out):
                continue
            todo += 1
            if done >= max_runs:
                continue
            if gpu_busy():
                print("GPU BUSY — stopping without launching.", flush=True)
                return
            cmd = ([sys.executable, "-u", TRAINER] + base + extra
                   + ["--save-ckpt", "--seed", str(seed), "--out", out])
            print(f"LAUNCH {os.path.basename(out)}", flush=True)
            with open(out.replace(".json", ".log"), "w", encoding="utf-8") as lf:
                rc = subprocess.run(cmd, stdout=lf,
                                    stderr=subprocess.STDOUT).returncode
            ok = os.path.exists(out.replace(".json", ".best.pt"))
            print(f"DONE   {os.path.basename(out)} rc={rc} ckpt={ok}", flush=True)
            if not ok:
                sys.exit(1)
            done += 1
    print(f"[{done} run(s) this invocation; {todo-done} remaining]", flush=True)
    if todo - done == 0:
        print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
