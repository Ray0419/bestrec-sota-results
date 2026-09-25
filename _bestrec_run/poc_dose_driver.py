# -*- coding: utf-8 -*-
"""PREREG_DOSE_RESPONSE_V1 driver: 2 arms x 5 seeds = 10 MI runs.

Each run carries the WHOLE dose-response (disjoint groups capped to
k in {0,1,2,4,8,16} plus a matched uncapped control), so 10 runs replace 60.
Checkpoints saved for the text arm only (the decomposition needs no ID table).
GPU-guarded, foreground, skip-if-exists.
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
SEEDS = (20260736, 20260737, 20260738, 20260739, 20260740)
EXCLUDE = {"seed", "out", "category", "save_ckpt", "eval_every",
           "fir_v3", "fir_v3_kernel", "fir_v3_wd", "zfusion_sweep"}
TEXT_KEYS = {"text_sim_bias", "text_prototypes"}
DOSE = ["--item-cap-multi", "0,1,2,4,8,16", "--item-cap-frac", "0.10",
        "--item-cap-min-deg", "20", "--item-cap-seed", "7"]
GPU_BUSY_MIB = 6000


def gpu_busy():
    try:
        o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                            "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=30)
        return int(o.stdout.strip().splitlines()[0]) >= GPU_BUSY_MIB
    except Exception:
        return False


def argv_for(cfg, id_arm):
    a = [cfg["category"]]
    for k in sorted(cfg):
        if k in EXCLUDE or cfg[k] is None or cfg[k] is False:
            continue
        if id_arm and k in TEXT_KEYS:
            continue
        f = "--" + k.replace("_", "-")
        a.append(f) if cfg[k] is True else a.extend([f, str(cfg[k])])
    if id_arm:
        a.append("--no-sbert")
    return a + ["--eval-every", "5"]


def main():
    max_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    cfg = json.load(open(REF, encoding="utf-8"))["config"]
    done = todo = 0
    for seed in SEEDS:
        for arm in ("text", "id"):
            out = os.path.join(OUT, f"results_DOSE_{arm}_MI_seed{seed}.json")
            if os.path.exists(out):
                continue
            todo += 1
            if done >= max_runs:
                continue
            if gpu_busy():
                print("GPU BUSY — stopping without launching.", flush=True)
                return
            cmd = ([sys.executable, "-u", TRAINER] + argv_for(cfg, arm == "id")
                   + DOSE + ["--seed", str(seed), "--out", out])
            if arm == "text":
                cmd.append("--save-ckpt")
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
