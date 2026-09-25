# -*- coding: utf-8 -*-
"""PREREG_TEMPORAL_V1 campaign: MI x5 seeds + VG x3 seeds, text arm.

Text arm only: every endpoint (E1 AUC gain, E2 efficiency ratio, E3 p*,
E4 aggregate effect) is a stock-vs-imputed contrast computed on a SINGLE
checkpoint, so no ID arm is needed. Scope discipline per LOOP3_SCOPE S7.3:
the dose-response is deliberately not reopened.

GPU-probed before every launch; the parallel session's lock is untouched.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN_RUN = r"C:\Users\rayxc\Documents\R\_bestrec_run"
OUT = os.path.join(HERE, "poc_out")
TRAINER = os.path.join(HERE, "run_sasrec_sbert_temporal.py")
EXCLUDE = {"seed", "out", "category", "save_ckpt", "eval_every",
           "fir_v3", "fir_v3_kernel", "fir_v3_wd", "zfusion_sweep"}
JOBS = [
    ("MI", "Musical_Instruments",
     os.path.join(MAIN_RUN, "results_MI_COLDFUSE_base_seed20260736.json"),
     (20260736, 20260737, 20260738, 20260739, 20260740)),
    ("VG", "Video_Games",
     os.path.join(MAIN_RUN, "results_VG_COLDFUSE_base_seed20260736.json"),
     (20260736, 20260737, 20260738, 20260739, 20260740)),  # 39-40: close E2 n=3->5
    # PREREG_STEAM_V1: sanity gate passed 2026-08-12 (LLOO test NDCG@10 = 0.0578,
    # inside the published full-ranking band and the pre-set [0.04, 0.20] gate).
    # 39-40 added per prereg S3 rule: E2 CI at n=3 spans 1.0 within +-1 SD
    ("STEAM", "Steam", None, (20260736, 20260737, 20260738, 20260739, 20260740)),
]
STEAM_ARGV = ["Steam", "--epochs", "20", "--batch-size", "256", "--d-model", "64",
              "--n-layers", "4", "--n-heads", "2", "--dropout", "0.5",
              "--encoder", "hstu", "--chunked-full-softmax", "--item-chunk", "32768",
              "--time-bias", "--pos-rab", "--label-smoothing", "0.2",
              "--causal-filter", "--filter-kernel", "16", "--text-sim-bias",
              "--text-prototypes", "512", "--lr-schedule", "warmup_cosine"]
GPU_BUSY_MIB = 6000


def gpu_busy():
    try:
        o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                            "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=30)
        return int(o.stdout.strip().splitlines()[0]) >= GPU_BUSY_MIB
    except Exception:
        return False


def argv_for(cfg):
    a = [cfg["category"]]
    for k in sorted(cfg):
        if k in EXCLUDE or cfg[k] is None or cfg[k] is False:
            continue
        f = "--" + k.replace("_", "-")
        a.append(f) if cfg[k] is True else a.extend([f, str(cfg[k])])
    return a + ["--eval-every", "20", "--temporal-split",
                "--temporal-inner-q", "0.60", "--temporal-outer-q", "0.75"]


def main():
    max_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    done = todo = 0
    for tag, cat, ref, seeds in JOBS:
        cfg = json.load(open(ref, encoding="utf-8"))["config"] if ref else None
        for seed in seeds:
            out = os.path.join(OUT, f"results_TEMP_{tag}_seed{seed}.json")
            if os.path.exists(out):
                continue
            todo += 1
            if done >= max_runs:
                continue
            if gpu_busy():
                print("GPU BUSY — stopping without launching.", flush=True)
                return
            base = (argv_for(cfg) if cfg else
                    STEAM_ARGV + ["--eval-every", "20", "--temporal-split",
                                  "--temporal-inner-q", "0.60",
                                  "--temporal-outer-q", "0.75"])
            cmd = ([sys.executable, "-u", TRAINER] + base
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
