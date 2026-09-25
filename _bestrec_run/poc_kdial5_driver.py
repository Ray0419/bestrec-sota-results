# -*- coding: utf-8 -*-
"""MERGED AGENDA step 1+2: 5-seed k-dial replication (MI), paired arms.

Grid: seeds x {text, id} x {anchor, k4, k0}. Arms are initialization-paired
within a seed (same seed/config; only the capped interactions differ). The
capped-item set is identical across every run (--item-cap-seed 7), so the
contrast is within-item as well as within-seed.

Checkpoints are saved for the text arm's anchor and k0 rungs only -- those are
the inputs to the offset-degeneracy decomposition (merged-agenda step 2).

COORDINATION: another session placed a PAUSE_EXPERIMENTS sentinel in this
worktree root to serialize GPU access. That file is NOT removed or modified.
Its purpose -- avoid GPU contention -- is honored directly instead: this driver
refuses to launch while the GPU is busy, and re-checks before every run.
Foreground-only (detached processes get reaped here); --max-runs per invocation
plus skip-if-exists makes progress durable across calls.
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
SEEDS = (20260736, 20260737, 20260738, 20260739, 20260740)
EXCLUDE = {"seed", "out", "category", "save_ckpt", "eval_every",
           "fir_v3", "fir_v3_kernel", "fir_v3_wd", "zfusion_sweep"}
TEXT_KEYS = {"text_sim_bias", "text_prototypes"}
CAP = ["--item-cap-frac", "0.25", "--item-cap-seed", "7"]
RUNGS = (("anchor", []),
         ("k4", ["--item-cap-k", "4"] + CAP),
         ("k0", ["--item-cap-k", "0"] + CAP))
# checkpoints only where the decomposition needs them
CKPT_FOR = {("text", "anchor"), ("text", "k0")}
GPU_BUSY_MIB = 6000          # a training job here holds ~7.6 GB; desktop ~2 GB


def gpu_busy():
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=30).stdout.strip().splitlines()
        return int(out[0].strip()) >= GPU_BUSY_MIB
    except Exception as e:                       # never block on a probe failure
        print(f"  (gpu probe failed: {e}; proceeding)", flush=True)
        return False


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
    return argv + ["--eval-every", "5"]


def main():
    max_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    cfg = json.load(open(REF, encoding="utf-8"))["config"]
    py = sys.executable
    done = 0
    todo = 0
    for seed in SEEDS:
        for arm in ("text", "id"):
            for rung, cap_args in RUNGS:
                out = os.path.join(
                    OUT_DIR, f"results_K5_{arm}_{rung}_MI_seed{seed}.json")
                if os.path.exists(out):
                    continue
                todo += 1
                if done >= max_runs:
                    continue
                if gpu_busy():
                    print("GPU BUSY (>=6 GB in use) — another job is running; "
                          "stopping this invocation without launching.", flush=True)
                    return
                cmd = ([py, "-u", TRAINER] + base_argv(cfg, arm == "id")
                       + cap_args + ["--seed", str(seed), "--out", out])
                if (arm, rung) in CKPT_FOR:
                    cmd.append("--save-ckpt")
                log = out.replace(".json", ".log")
                print(f"LAUNCH {os.path.basename(out)}", flush=True)
                with open(log, "w", encoding="utf-8") as lf:
                    rc = subprocess.run(cmd, stdout=lf,
                                        stderr=subprocess.STDOUT).returncode
                print(f"DONE   {os.path.basename(out)} rc={rc}", flush=True)
                if rc != 0:
                    print(f"ABORT rc={rc}; see {log}", flush=True)
                    sys.exit(rc)
                done += 1
    remaining = todo - done
    print(f"[{done} run(s) this invocation; {remaining} remaining]", flush=True)
    if remaining == 0:
        print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
