# -*- coding: utf-8 -*-
"""Rigor-review Q1/Q3/Q4 evidence campaign (eval-only, no training).

INNER-window evals (all 15 checkpoints): give g,c -> p*_inner for the
out-of-sample prediction test (Q1), plus fusion sweep cells for tuning
selection (Q3) and invasion instrumentation (Q4).
OUTER-window fusion sweeps (Steam only): the tuned-vs-transferred report (Q3).

Strides (deterministic every-Nth-event thinning, declared in every artifact):
MI 1, VG 2, STEAM 4 — keeps per-eval wall time bounded at Steam's event scale.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "poc_out")
EVAL = os.path.join(HERE, "poc_temporal_eval.py")
SWEEP = "0.05,0.1,0.5,1.0"          # 0.2 comes free as the family 'fusion' arm
SEEDS = (20260736, 20260737, 20260738, 20260739, 20260740)
STRIDE = {"MI": 1, "VG": 2, "STEAM": 4}
GPU_BUSY_MIB = 6000


def gpu_busy():
    try:
        o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                            "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=30)
        return int(o.stdout.strip().splitlines()[0]) >= GPU_BUSY_MIB
    except Exception:
        return False


def jobs():
    for tag in ("MI", "VG", "STEAM"):
        for seed in SEEDS:
            src = os.path.join(OUT, f"results_TEMP_{tag}_seed{seed}.json")
            dst = os.path.join(OUT, f"results_TEMP_{tag}_seed{seed}.inner_eval.json")
            yield (src, dst, ["--window", "inner", "--family",
                              "--fusion-sweep", SWEEP,
                              "--event-stride", str(STRIDE[tag])])
    for seed in SEEDS:
        src = os.path.join(OUT, f"results_TEMP_STEAM_seed{seed}.json")
        dst = os.path.join(OUT, f"results_TEMP_STEAM_seed{seed}.outer_sweep.json")
        yield (src, dst, ["--window", "outer", "--family",
                          "--fusion-sweep", SWEEP,
                          "--event-stride", str(STRIDE["STEAM"])])


def main():
    max_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    done = todo = 0
    for src, dst, extra in jobs():
        if not os.path.exists(src) or os.path.exists(dst):
            continue
        todo += 1
        if done >= max_runs:
            continue
        if gpu_busy():
            print("GPU BUSY — stopping without launching.", flush=True)
            return
        log = dst.replace(".json", ".log")
        print(f"EVAL {os.path.basename(dst)}", flush=True)
        with open(log, "w", encoding="utf-8") as lf:
            rc = subprocess.run([sys.executable, "-u", EVAL, src,
                                 "--out", dst] + extra,
                                stdout=lf, stderr=subprocess.STDOUT).returncode
        print(f"  rc={rc}", flush=True)
        if rc != 0:
            sys.exit(rc)
        done += 1
    print(f"[{done} eval(s) this invocation; {todo-done} remaining]", flush=True)
    if todo - done == 0:
        print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
