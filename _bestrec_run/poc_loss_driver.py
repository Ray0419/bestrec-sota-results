# -*- coding: utf-8 -*-
"""PREREG_LOSS_V1: gBCE (gSASRec, credited) vs full-CE under the temporal protocol."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "poc_out")
TRAINER = os.path.join(HERE, "run_sasrec_sbert_temporal.py")
SEEDS = (20260736, 20260737, 20260738)
BASE = ["Musical_Instruments", "--epochs", "20", "--batch-size", "256",
        "--d-model", "64", "--n-layers", "4", "--n-heads", "2",
        "--dropout", "0.5", "--encoder", "hstu", "--item-chunk", "32768",
        "--time-bias", "--pos-rab", "--causal-filter", "--filter-kernel", "16",
        "--text-sim-bias", "--text-prototypes", "512",
        "--lr-schedule", "warmup_cosine", "--temporal-split",
        "--gbce-t", "0.75", "--gbce-negs", "256", "--eval-every", "20"]


def gpu_busy():
    try:
        o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                            "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=30)
        return int(o.stdout.strip().splitlines()[0]) >= 6000
    except Exception:
        return False


def main():
    mx = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    done = todo = 0
    for seed in SEEDS:
        out = os.path.join(OUT, f"results_LOSS_gbce_MI_seed{seed}.json")
        if os.path.exists(out):
            continue
        todo += 1
        if done >= mx:
            continue
        if gpu_busy():
            print("GPU BUSY — stopping.", flush=True)
            return
        cmd = ([sys.executable, "-u", TRAINER] + BASE
               + ["--save-ckpt", "--seed", str(seed), "--out", out])
        print(f"LAUNCH {os.path.basename(out)}", flush=True)
        with open(out.replace(".json", ".log"), "w", encoding="utf-8") as lf:
            rc = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT).returncode
        ok = os.path.exists(out.replace(".json", ".best.pt"))
        print(f"DONE   rc={rc} ckpt={ok}", flush=True)
        if not ok:
            sys.exit(1)
        done += 1
    print(f"[{done} run(s); {todo-done} remaining]", flush=True)
    if todo - done == 0:
        print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
